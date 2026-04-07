from time import strftime, strptime

import eventlet
eventlet.monkey_patch()

from flask import Flask, request
from flask_socketio import SocketIO, emit
import secrets
from datetime import datetime
from datetime import timedelta

from database import db, User, Friendship, BlockedUser, FriendRequest, Message
from retention_policy import start_retention_worker
#from Email import emailVerification

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
pending_otps = {}   # email -> otp (for registration/login verification)

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
    
    # only for testing!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    #should use email.py to send email with OTP!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Generate and store OTP
    generated_otp = secrets.randbelow(900000) + 100000  # 生成 6 位数 OTP
    pending_otps[email] = generated_otp
    print(f"Generated OTP for {email}: {generated_otp}")
    
    return {'success': True, 'message': 'OTP generated', 'otp': generated_otp}

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
    
    if otp != str(pending_otps.get(email)).strip():
        return {'success': False, 'error': 'Invalid OTP'}
    
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

    #need to remove!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    print(f"from {email}: {otp}") #need to remove!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    #need to remove!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    
    if token and token in sessions:
        # Token-based authentication (auto-login)
        cached_user = sessions[token]
        
        if token_map[token] > datetime.now():
            
            # Update current connection mapping
            user = cached_user
            email = cached_user.email
            
            if email and user_sid_map.get(email):
                return {'success': False, 'error': 'User already logged in from another device'}
    
            sid = request.sid
            online_users[sid] = email
            user_sid_map[email] = sid
            
            print(f"Auto-login successful: {email}")
            
            sessions[token] = cached_user
            
            token_expiry_time = token_map[token]    
            
        else:
            # remove expired token
            if token in token_map:
                del token_map[token]
            return {'success': False, 'error': 'Invalid or expired token'}
        
    else:        
        # Credential-based authentication
        user = find_user_by_email(email)
        
        # Validate credentials
        if not user or user.password != password:
            return {'success': False, 'error': 'Invalid credentials'}
        
        # Validate OTP
        if not otp or otp != str(pending_otps.get(email)).strip():
            return {'success': False, 'error': 'Invalid OTP'}
        
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
    offline_msgs_query = Message.query.filter_by(to_email=user.email, delivered=False).all()
    
    if offline_msgs_query:
        delivery_notifications = {} # Group notifications by sender
        formatted_msgs = []
        for m in offline_msgs_query:
            formatted_msgs.append({
                'message_id': m.id,
                'from_email': m.from_email,
                'to_email': m.to_email,
                'content': m.content,
                'timestamp': m.timestamp.isoformat() if m.timestamp else None,
                'macAddress': m.macAddress,
                'del_time': m.del_time
            })
            m.delivered = True
            
            # Track which messages need delivery notifications sent to the sender
            if m.from_email not in delivery_notifications:
                delivery_notifications[m.from_email] = []
            delivery_notifications[m.from_email].append(m.id)
            
        # Notify senders immediately if they are currently online
        for sender_email, msg_ids in delivery_notifications.items():
            if sender_email in user_sid_map:
                socketio.emit('message_delivered', {
                    'receiver': user.email,
                    'message_id_list': msg_ids,
                    }, room=user_sid_map[sender_email])
                # Mark as notified since we just sent the receipt to the online sender
                for mid in msg_ids:
                    msg_obj = Message.query.get(mid)
                    msg_obj.delivery_notified = True
            
        try:
            db.session.commit()
            print(f"Successfully synchronized offline status for {user.email}")
        except Exception as e:
            db.session.rollback()
            print(f"Database sync error: {e}")
            
        emit('offline_messages', formatted_msgs)
        
    # Send offline delivery receipts for messages sent by this user that were delivered while they were offline
    undelivered_receipts = Message.query.filter_by(from_email=user.email, delivered=True, delivery_notified=False).all()
    if undelivered_receipts:
        receipt_ids = [m.id for m in undelivered_receipts]
        emit('message_delivered', {'message_id_list': receipt_ids})
        for m in undelivered_receipts:
            m.delivery_notified = True
        db.session.commit()
    
    
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
            if user['email'] == email:
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
    macAddress = data.get('macAddress')
    lifetime = data.get('lifetime', None)
    
    if lifetime is not None: 
        print("Lifetime")
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
            delivery_notified=False,
            macAddress=macAddress,
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
                'macAddress': macAddress,
                'del_time': del_time,
            }, room=user_sid_map[to_email])
            
            new_msg.delivered = True
            new_msg.delivery_notified = True
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
    latest_msg = Message.query.filter_by(
        from_email=friend_email,
        to_email=user_email, 
        delivered=True
    ).order_by(Message.id.desc()).first()
    
    if latest_msg:
        return {'success': True, 'latest_message_id': latest_msg.id}
    else:
        return {'success': True, 'latest_message_id': None}

# ============ Server Startup ============

if __name__ == '__main__':
    print("=" * 50)
    print("Chat Server Starting")
    print("=" * 50)
    
    with app.app_context():
        db.create_all()
    
    start_retention_worker(app)
    
    from os.path import join, abspath, dirname
    cur = dirname(abspath(__file__))
    socketio.run(app, host='0.0.0.0', port=3000, debug=True, keyfile=join(cur, 'key.pem'), certfile=join(cur, 'cert.pem'))