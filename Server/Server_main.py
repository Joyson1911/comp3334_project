from time import strftime, strptime

import eventlet
eventlet.monkey_patch()

from flask import Flask, request
from flask_socketio import SocketIO, emit
import secrets
from datetime import datetime
from datetime import timedelta
from sqlalchemy import or_

from database import db, User, Friendship, BlockedUser, FriendRequest, Message
from retention_policy import start_retention_worker
from otp_cleanup import start_otp_cleanup
from Email import emailVerification

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Online user management
online_users = {}    # sid -> user_email
user_sid_map = {}    # user_email -> sid
sessions = {}        # token -> user
token_map = {}      # token -> token_expiry_time
pending_otps = {}   # email -> otp and otp_expiry_time (for registration/login verification)

otp_lifetime = timedelta(minutes=5)  # OTP lifetime 

# ============ Helper Functions ============

def find_user_by_email(email) -> User:
    """Find user by email address"""
    return User.query.filter_by(email=email).first()

def generate_token():
    """Generate a secure random token for authentication"""
    return secrets.token_urlsafe(32), datetime.now() + timedelta(hours=24)

# ============ WebSocket Event Handlers ============

@socketio.on('connect')
def handle_connect():
    """Allow initial WebSocket connection so users can send registration/login requests"""
    sid = request.sid
    print(f"Detected new connection (sid={sid}), waiting for authentication...")
    
    emit('connected', {
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection and cleanup"""
    sid = request.sid
    if sid in online_users:
        email = online_users[sid]
        print(f"{email} disconnected")
        del online_users[sid]
        if email in user_sid_map:
            del user_sid_map[email]

# ============ Authentication Events ============

@socketio.on('otp_request')
def handle_otp_request(data):
    """
    Request a new OTP for email verification
    Expected data: {email}
    """
    email = data.get('email')
    action = data.get('action')
    
    if not email:
        return {'success': False, 'error': 'Email is required'}
    
    if action == 'register':
        # Check if email already exists in registration
        if find_user_by_email(email):
            return {'success': False, 'error': 'User (Email) already exists'}
        
    if action == 'login':
        # Check if email exists for login
        if not find_user_by_email(email):
            return {'success': False, 'error': 'User (Email) not found'}
    
    # Generate and store OTP
    generated_otp = secrets.randbelow(900000) + 100000  # 6-digit OTP
    expiry_time = datetime.now() + otp_lifetime
    pending_otps[email] = {
        'code': str(generated_otp),
        'expiry': expiry_time
    }
    
    # emailVerification(generated_otp, email)
    print(f"Generated OTP for {email}: {generated_otp} (expires at {expiry_time.isoformat()})")
    
    return {'success': True, 'message': 'OTP generated'}

@socketio.on('register')
def handle_register(data):
    """
    Register a new user account
    Expected data: {email, password, otp}
    """
    email = data.get('email')
    password = data.get('password')
    otp = str(data.get('otp')).strip()
    
    # Validate input
    if not email or not password or not otp:
        return {'success': False, 'error': 'Email, password, and OTP are required'}
    
    if otp != str(pending_otps.get(email or {}).get("code")).strip():
        return {'success': False, 'error': 'Invalid OTP'}
    
    # Check if OTP has expired
    if datetime.now() > pending_otps.get(email or {}).get("expiry"):
        pending_otps.pop(email, None) # Remove expired OTP
        return {'success': False, 'error': 'OTP has expired'}
    
    # OTP is valid, remove it from pending list
    pending_otps.pop(email, None)
    
    try:
        new_user = User(
            email = email,
            password = password,
            macAddress = None,
            publicKey = None,
            created_at = datetime.utcnow() 
        )
        db.session.add(new_user)
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': f'Database error occurred: {str(e)}'}
    
    return {'success': True, 'message': 'Registered successfully', 'user': {'email': email}}

@socketio.on('login')
def handle_login(data):
    """
    Authenticate user and establish session
    Expected data: {token} for auto-login or {email, password, otp} for credential-based login
    """
    token = data.get('token')

    email = data.get('email')
    password = data.get('password')
    otp = str(data.get('otp')).strip()
    
    macAddress = data.get('macAddress')
    publicKey = data.get('publicKey')
    
    if token and token in sessions:
        
        user = sessions[token]
        email = user.email
        
        # Validate token expiry
        expiry_time = token_map.get(token)
        if not expiry_time or expiry_time <= datetime.now():
            # Token expired, remove session and token
            sessions.pop(token, None)
            token_map.pop(token, None)
            return {'success': False, 'error': 'Invalid or expired token'}
        
        if email and user_sid_map.get(email):
            return {'success': False, 'error': 'User already logged in from another device'}
        
        # Update current connection mapping
        sid = request.sid
        online_users[sid] = email
        user_sid_map[email] = sid
        
        token_expiry_time = expiry_time
        
        print(f"Auto-login successful: {email}")    
            

    else:        
        # Credential-based authentication
        user = find_user_by_email(email)
        
        # Validate credentials
        if not user or user.password != password:
            return {'success': False, 'error': 'Invalid credentials'}
        
        # Validate OTP
        if not otp or otp != str(pending_otps.get(email or {}).get("code")).strip():
            return {'success': False, 'error': 'Invalid OTP'}
        
        # Check if OTP has expired
        if datetime.now() > pending_otps.get(email or {}).get("expiry"):
            pending_otps.pop(email, None) # Remove expired OTP
            return {'success': False, 'error': 'OTP has expired'}
        
        if email and user_sid_map.get(email):
            return {'success': False, 'error': 'User already logged in from another device'}
        
        # OTP is valid, remove it from pending list
        pending_otps.pop(email, None)

        # Generate access token
        token, token_expiry_time = generate_token()
        
        sessions[token] = user
        
        # Update current connection mapping
        sid = request.sid
        online_users[sid] = email
        user_sid_map[email] = sid
        
        # Update user's device info
        user.macAddress = macAddress
        user.publicKey = publicKey
        db.session.commit()
    
    # Send offline messages if any
    offline_msgs_query = Message.query.filter_by(to_email=user.email, delivered=False, to_macAddress=user.macAddress).all()
    
    if offline_msgs_query:
        formatted_msgs = []
        for m in offline_msgs_query:
            formatted_msgs.append({
                'message_id': m.id,
                'from_email': m.from_email,
                'to_email': m.to_email,
                'content': m.content,
                'timestamp': m.timestamp.isoformat() if m.timestamp else None,
                'to_macAddress': find_user_by_email(m.to_email).macAddress if find_user_by_email(m.to_email) else None,
                'del_time': m.del_time
            })
            m.delivered = True
            
        try:
            db.session.commit()
            print(f"Successfully synchronized offline status for {user.email}")
        except Exception as e:
            db.session.rollback()
            print(f"Database sync error: {e}")
            
        emit('offline_messages', formatted_msgs)
        
    
    # Send offline friend requests if any
    offline_reqs_query = FriendRequest.query.filter_by(to_email=user.email, status='pending').all()
    
    if offline_reqs_query:
        formatted_reqs = [{
            'from_email': r.from_email,
            'timestamp': r.created_at.isoformat() if r.created_at else None
        } for r in offline_reqs_query]
    
        print(f"Sending {len(formatted_reqs)} offline friend requests to {user.email}")
        emit('offline_friend_requests', formatted_reqs)
    
    #need to remove!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    print(f"token: {token}") #need to remove!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    #need to remove!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    
    token_map[token] = token_expiry_time
    
    user_friends = Friendship.query.filter_by(user_email=email).all()
    user_blocked = BlockedUser.query.filter_by(user_email=email).all()
    
    return {
        'success': True, 
        'access_token': token,
        'email': email, 
        'token_expiry_time': token_expiry_time.isoformat(),
        'friends_list': [f.friend_email for f in user_friends],
        'blocked_list': [b.blocked_email for b in user_blocked]
    }


@socketio.on('logout')
def handle_logout(data):
    """
    Logout user and clear session
    """
    sid = request.sid
    if sid in online_users:
        email = online_users[sid]
        del online_users[sid]
        if email in user_sid_map:
            del user_sid_map[email]
        
        # Clear all sessions for this user
        for token, user in list(sessions.items()):
            if user.email == email:
                del sessions[token]
                break
        
        emit('logout_response', {'success': True})

# ============ Friend Management Events ============

@socketio.on('send_friend_request')
def handle_send_friend_request(data):
    """
    Send a friend request to another user
    Expected data: {user_email}
    """
    sid = request.sid
    if sid not in online_users:
        return {'success': False, 'error': 'Not authenticated'}
    
    # User sending the request
    user_email = online_users[sid]
    
    # User receiving the request
    friend_email = data.get('user_email')
    
    if not friend_email:
        return {'success': False, 'error': 'User email required'}
    
    friend = find_user_by_email(friend_email)
    if not friend:
        return {'success': False, 'error': 'User not found'}
    
    if friend_email == user_email:
        return {'success': False, 'error': 'Cannot add yourself'}
    
    # Check if request already exists
    existing_request = FriendRequest.query.filter_by(
        from_email=user_email, 
        to_email=friend_email, 
        status='pending'
    ).first()
    if existing_request:
        return {'success': False, 'error': 'Request already sent'}
    
    # Check if already friends
    is_already_friend = Friendship.query.filter_by(
        user_email=user_email, 
        friend_email=friend_email
    ).first()
    if is_already_friend:
        return {'success': False, 'error': 'Already friends'}
    
    # Create friend request
    try:
        new_request = FriendRequest(
            from_email=user_email,
            to_email=friend_email,
            status='pending',
            created_at=datetime.utcnow()
        )
        db.session.add(new_request)
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': f'Database error occurred: {str(e)}'}
     
    # Real-time notification if recipient is online
    if friend_email in user_sid_map:
        socketio.emit('friend_request_received', {
            'from_email': user_email,
            'to_email': friend_email,
        }, room=user_sid_map[friend_email])
    
    return {'success': True, 'message': 'Request sent'}

@socketio.on('respond_to_friend_request')
def handle_respond_to_friend_request(data):
    """
    Handle accepting or rejecting a friend request
    Expected data: {request_id, action: "accept" | "reject"}
    """
    sid = request.sid
    if sid not in online_users:
        return {'success': False, 'error': 'Not authenticated'}
    
    user_email = online_users[sid]
    friend_email = data.get('friend_email')
    action = data.get('action')
    
    # Find the request
    req = FriendRequest.query.filter_by(
        from_email=friend_email, 
        to_email=user_email,
        status='pending'
    ).first()
    
    if not req or req.to_email != user_email:
        return {'success': False, 'error': 'Request not found'}
    
    if req.status != 'pending':
        return {'success': False, 'error': 'Request already processed'}
    
    # Update request status
    try:
        if action == 'accept':
            req.status = 'accepted'
        
            # Add bidirectional friendship
            f1 = Friendship(user_email=req.from_email, friend_email=req.to_email)
            f2 = Friendship(user_email=req.to_email, friend_email=req.from_email)
            db.session.add(f1)
            db.session.add(f2)
            db.session.commit()
        
            # Notify the requester in real-time
            if req.from_email in user_sid_map:
                socketio.emit('friend_request_accepted', {
                    'friend_email': req.to_email,
                    'message': f"{req.to_email} accepted your friend request"
                }, room=user_sid_map[req.from_email])
                
        elif action == 'reject':

            # Notify the requester in real-time
            if req.from_email in user_sid_map:
                socketio.emit('friend_request_rejected', {
                    'from_email': req.to_email,
                }, room=user_sid_map[req.from_email])
                
            db.session.delete(req) 
            db.session.commit()
            
        else:
            return {'success': False, 'error': 'Invalid action'}
    
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': f'Database error occurred: {str(e)}'}
    
    return {'success': True, 'message': f'Request {action}ed successfully'}

@socketio.on('unfriend_request')
def handle_unfriend_request(data):
    """
    Handle unfriending a user
    Expected data: {friend_email, action}
    """
    sid = request.sid
    if sid not in online_users:
        return {'success': False, 'error': 'Not authenticated'}
    
    user_email = online_users[sid]
    friend_email = data.get('friend_email')
    action = data.get('action')
    
    if not friend_email:
        return {'success': False, 'error': 'Friend email required'}
    
    if friend_email == user_email:
        return {'success': False, 'error': 'Cannot unfriend yourself'}
    
    try:
        f1 = Friendship.query.filter_by(user_email=user_email, friend_email=friend_email).first()
        f2 = Friendship.query.filter_by(user_email=friend_email, friend_email=user_email).first()
        
        # Check if they are actually friends
        if action == "remove" and not f1:
            return {'success': False, 'error': 'Not friends'}
            
        if f1: db.session.delete(f1)
        if f2: db.session.delete(f2)
    
        if action == "block":
            already_blocked = BlockedUser.query.filter_by(
                    user_email=user_email, 
                    blocked_email=friend_email
            ).first()
        
            if not already_blocked:
                    new_block = BlockedUser(
                        user_email=user_email,
                        blocked_email=friend_email
                    )
                    db.session.add(new_block)
                
            db.session.commit()
                
            current_blocked = BlockedUser.query.filter_by(user_email=user_email).all()
            return {
                'success': True, 
                'message': 'User blocked successfully', 
                'blocked_list': [b.blocked_email for b in current_blocked]
            }
                
        db.session.commit()
        return {'success': True, 'message': 'Friend removed successfully'}
    
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': f'Database error: {str(e)}'}

@socketio.on('cancel_friend_request')    
def handle_cancel_friend_request(data):
    """
    Handle canceling a sent friend request
    Expected data: {friend_email}
    """
    sid = request.sid
    if sid not in online_users:
        return {'success': False, 'error': 'Not authenticated'}
    
    user_email = online_users[sid]
    friend_email = data.get('friend_email')
    
    if not friend_email:
        return {'success': False, 'error': 'Friend email required'}
    
    try:
        req = FriendRequest.query.filter_by(
            from_email=user_email, 
            to_email=friend_email, 
            status='pending'
        ).first()
        
        if not req:
            return {'success': False, 'error': 'Pending request not found'}
        
        db.session.delete(req)
        db.session.commit()
        
        return {'success': True, 'message': 'Friend request canceled'}
    
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': f'Database error: {str(e)}'}

# ============ Messaging Events ============

@socketio.on('get_public_key')
def handle_get_public_key(data):
    """
    Get a user's public key for end-to-end encryption
    Expected data: {friend_email}
    """
    sid = request.sid
    if sid not in online_users:
        return {'success': False, 'error': 'Not authenticated'}
    
    user_email = online_users[sid]
    friend_email = data.get('friend_email')
    
    friend = find_user_by_email(friend_email)
    if not friend:
        return {'success': False, 'error': 'Friend not found'}
    
    # Check if they are friends before sharing public key
    # Only allow fetching public key if they are friends
    is_friend = Friendship.query.filter_by(
        user_email=user_email, 
        friend_email=friend_email
    ).first() 
    if not is_friend:
        return {'success': False, 'error': 'You can only get public keys of your friends'}
    
    return {'success': True, 'public_key': friend.publicKey}

@socketio.on('send_message')
def handle_send_message(data):
    """
    Send a message to a friend
    Expected data: {to_email, content, timestamp (optional)}
    """
    sid = request.sid
    if sid not in online_users:
        return {'success': False, 'error': 'Not authenticated'}
    
    from_email = online_users[sid]
    to_email = data.get('to_email')
    content = data.get('content')
    lifetime = data.get('lifetime', None)
    
    if lifetime is not None: 
        del_time = datetime.now()+timedelta(seconds=lifetime)
        del_time = del_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        del_time = None 
    
    # Validate input
    if not to_email or not content:
        return {'success': False, 'error': 'Recipient and content required'}
    
    try:
        # Verify they are friends
        is_friend = Friendship.query.filter_by(
            user_email=from_email, 
            friend_email=to_email
        ).first()
        
        if not is_friend:
            return {'success': False, 'error': 'You can only message your friends'}
        
        # Check if recipient has blocked the sender
        is_blocked = BlockedUser.query.filter_by(
            user_email=to_email, 
            blocked_email=from_email
        ).first()
        
        if is_blocked:
            return {'success': False, 'error': 'Message failed: You are blocked by this user'}
        
        # Create message object
        new_msg = Message(
            from_email=from_email,
            to_email=to_email,
            content=content,
            timestamp=datetime.utcnow(),
            delivered=False,
            to_macAddress=find_user_by_email(to_email).macAddress if find_user_by_email(to_email) else None,
            del_time=del_time
        )
        
        db.session.add(new_msg)
        db.session.flush()  # Flush to get the message ID for real-time delivery before commit
        
        # Check if recipient is online
        delivered = False
        if to_email in user_sid_map:
            # Online - deliver immediately
            socketio.emit('new_message', {
                'message_id': new_msg.id,
                'from_email': from_email,
                'to_email': to_email,
                'content': content,
                'timestamp': new_msg.timestamp.isoformat(),
                'to_macAddress': find_user_by_email(to_email).macAddress if find_user_by_email(to_email) else None,
                'del_time': del_time,
            }, room=user_sid_map[to_email])
            
            new_msg.delivered = True
            delivered = True
            
        db.session.add(new_msg)
        db.session.commit()
        
        return {
            'success': True, 
            'message_id': new_msg.id,
            'delivered': delivered,
            'del_time': del_time
        }
        
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': f'Database error: {str(e)}'}
    
@socketio.on('latest_message_id')
def handle_latest_message_id(data):
    """
    Get the latest message ID from a friend for synchronization
    Expected data: {friend_email}
    """
    sid = request.sid
    if sid not in online_users:
        return {'success': False, 'error': 'Not authenticated'}
    
    user_email = online_users[sid]
    friend_email = data.get('friend_email')
    
    if not friend_email:
        return {'success': False, 'error': 'Friend email required'}
    
    # Check if they are friends
    is_friend = Friendship.query.filter_by(
        user_email=user_email, 
        friend_email=friend_email
    ).first()
    
    if not is_friend:
        return {'success': False, 'error': 'You can only get message IDs from your friends'}
    
    # Get the latest message ID
    latest_msg = Message.query.filter(
        or_(
            (Message.from_email == friend_email) & (Message.to_email == user_email),
            (Message.from_email == user_email) & (Message.to_email == friend_email)
        ),
        Message.delivered == True
    ).order_by(Message.id.desc()).first()
    
    if latest_msg:
        return {'success': True, 'latest_message_id': latest_msg.id}
    else:
        return {'success': True, 'latest_message_id': 0}

# ============ Server Startup ============

if __name__ == '__main__':
    print("=" * 50)
    print("Chat Server Starting")
    print("=" * 50)
    
    with app.app_context():
        db.create_all()
    
    # Start background worker for message retention policy
    start_retention_worker(app)
    
    # Start background worker for OTP cleanup
    start_otp_cleanup(pending_otps)
    
    from os.path import join, abspath, dirname
    cur = dirname(abspath(__file__))
    socketio.run(app, host='0.0.0.0', port=3000, debug=True, keyfile=join(cur, 'key.pem'), certfile=join(cur, 'cert.pem'))