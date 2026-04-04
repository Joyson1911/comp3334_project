import eventlet
eventlet.monkey_patch()

from flask import Flask, request
from flask_socketio import SocketIO, emit, disconnect, ConnectionRefusedError
import secrets
from datetime import datetime
from datetime import timedelta
#from Email import emailVerification

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory storage (replace with database in production !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!)
users = []           # {id, email, password, otp, created_at, macAddress, publicKey}  
friends = []         # {user_email, friend_email, created_at}
blocked = []           # {user_email, blocked_email}
friend_requests = [] # {from_email, to_email, status, created_at}  
messages = []        # {id, from_email, to_email, content, timestamp, delivered, macAddress} 

# Online user management
online_users = {}    # sid -> user_email
user_sid_map = {}    # user_email -> sid
sessions = {}        # token -> user
token_map = {}      # token -> token_expiry_time
pending_otps = {}   # email -> otp (for registration/login verification)

otp_lifetime = timedelta(minutes=5)  # OTP lifetime 

# ============ Helper Functions ============

def find_user_by_email(email):
    """Find user by email address"""
    for user in users:
        if user['email'] == email:
            return user
    return None

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
    
    # Create new user
    new_user = {
        'id': len(users) + 1,
        'email': email,
        'password': password,
        'otp': otp,
        'macAddress': None,
        'publicKey': None,
        'created_at': datetime.now().isoformat()
    }
    users.append(new_user)
    
    return {'success': True, 'message': 'Registered successfully', 'user': {'email': email}}

@socketio.on('login')
def handle_login(data):
    """
    Authenticate user and establish session
    Expected data: {token} or {email, password, otp}
    """
    token = data.get('token')

    email = data.get('email')
    password = data.get('password')
    otp = str(data.get('otp')).strip()
    
    macAddress = data.get('macAddress')
    publicKey = data.get('publicKey')

    print(f"from {email}: {otp}") #need to remove!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    if token:
        # Token-based authentication (auto-login)
        if token in sessions and token_map[token] > datetime.now():
            user = sessions[token]
            email = user['email']
            # Update current connection mapping
            sid = request.sid
            online_users[sid] = email
            user_sid_map[email] = sid
            print(f"Auto-login successful: {email}")
            
            token_expiry_time = token_map[token]    
        else:
            return {'success': False, 'error': 'Invalid or expired token'}
        
    else:        
        # Credential-based authentication
        user = find_user_by_email(email)
        
        # Validate credentials
        if not user or user['password'] != password or not otp:
            return {'success': False, 'error': 'Invalid credentials'}
        
        if otp != str(pending_otps.get(email)).strip():
            return {'success': False, 'error': 'Invalid OTP'}

        # Generate access token
        token, token_expiry_time = generate_token()
        
        sessions[token] = user
        
        # Update current connection mapping
        sid = request.sid
        online_users[sid] = email
        user_sid_map[email] = sid
        
        # Update user's device info
        user['macAddress'] = macAddress
        user['publicKey'] = publicKey
    
    # Send offline messages if any
    offline_msgs = [
        msg for msg in messages 
        if msg['to_email'] == user['email'] and not msg.get('delivered', False)
    ]
    if offline_msgs:
        print(f"Sending {len(offline_msgs)} offline messages to {user['email']}")
        emit('offline_messages', offline_msgs)
    
    # Send pending friend requests if any
    offline_reqs = [
        req for req in friend_requests 
        if req['to_email'] == user['email'] and req['status'] == 'pending'
    ]
    if offline_reqs:
        print(f"Sending {len(offline_reqs)} offline friend requests to {user['email']}")
        emit('offline_friend_requests', offline_reqs)
    
    print(f"token: {token}")
    
    token_map[token] = token_expiry_time
    
    return {
        'success': True, 
        'access_token': token,
        'user': {'email': email}, 
        'token_expiry_time': token_expiry_time.isoformat(),
        'friends_list': [f['friend_email'] for f in friends if f['user_email'] == email],
        'blocked_list': [b['blocked_email'] for b in blocked if b['user_email'] == email]
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
    
    user_email = online_users[sid]
    friend_email = data.get('user_email')
    
    if not friend_email:
        return {'success': False, 'error': 'User email required'}
    
    friend = find_user_by_email(friend_email)
    if not friend:
        return {'success': False, 'error': 'User not found'}
    
    if friend_email == user_email:
        return {'success': False, 'error': 'Cannot add yourself'}
    
    if any(f for f in friend_requests if f['from_email'] == user_email and f['to_email'] == friend_email):
        return {'success': False, 'error': 'Request already sent'}
    
    # Check if already friends
    if any(f for f in friends if f['user_email'] == user_email and f['friend_email'] == friend_email):
        return {'success': False, 'error': 'Already friends'}
    
    # Create friend request
    new_request = {
        # 'id': len(friend_requests) + 1,
        'from_email': user_email,
        'to_email': friend_email,
        'status': 'pending',
    }
    friend_requests.append(new_request)
    
    # Real-time notification if recipient is online
    if friend_email in user_sid_map:
        socketio.emit('friend_request_received', {
            'from_email': user_email,
            'to_email': friend_email,
        }, room=user_sid_map[friend_email])
    
    return {'success': True, 'message': 'Request sent', 'request_id': new_request['id']}

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
    req_id = data.get('request_id')
    action = data.get('action')
    
    # Find the request
    req = next((r for r in friend_requests if r['id'] == req_id), None)
    if not req or req['to_email'] != user_email:
        return {'success': False, 'error': 'Request not found'}
    
    if req['status'] != 'pending':
        return {'success': False, 'error': 'Request already processed'}
    
    # Update request status
    if action == 'accept':
        req['status'] = 'accepted'
    
        # Add bidirectional friendship
        friends.append({
            'user_email': req['from_email'],
            'friend_email': req['to_email'],
            'created_at': datetime.now().isoformat()
        })
        friends.append({
            'user_email': req['to_email'],
            'friend_email': req['from_email'],
            'created_at': datetime.now().isoformat()
        })
    
        # Notify the requester in real-time
        if req['from_email'] in user_sid_map:
            socketio.emit('friend_request_accepted', {
                'friend_email': req['to_email'],
                'message': f"{req['to_email']} accepted your friend request"
            }, room=user_sid_map[req['from_email']])
            
    elif action == 'reject':
        req['status'] = 'rejected'
        
        # Notify the requester in real-time
        if req['from_email'] in user_sid_map:
            socketio.emit('friend_request_rejected', {
                'from_email': req['to_email'],
                'request_id': req_id
            }, room=user_sid_map[req['from_email']])
            
    else:
        return {'success': False, 'error': 'Invalid action'}
    
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
    
    if action == "remove":
        # Check if they are actually friends
        if not any(f for f in friends if f['user_email'] == user_email and f['friend_email'] == friend_email):
            return {'success': False, 'error': 'Not friends'}
    
        # Find and remove the friendship
        friends.remove((f for f in friends if f['user_email'] == user_email and f['friend_email'] == friend_email))
        friends.remove((f for f in friends if f['user_email'] == friend_email and f['friend_email'] == user_email))
    
    if action == "block":
        if any(f for f in friends if f['user_email'] == user_email and f['friend_email'] == friend_email):
            # Find and remove the friendship
            friends.remove((f for f in friends if f['user_email'] == user_email and f['friend_email'] == friend_email))
            friends.remove((f for f in friends if f['user_email'] == friend_email and f['friend_email'] == user_email))
            
        blocked.append({
            'user_email': user_email,
            'blocked_email': friend_email,
        })
        return {'success': True, 'message': 'Friend removed successfully', 'blocked_list': [b['blocked_email'] for b in blocked if b['user_email'] == user_email]}
    
    return {'success': True, 'message': 'Friend removed successfully'}

# ============ Messaging Events ============

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
    timestamp = data.get('timestamp', datetime.now().isoformat())
    
    # Validate input
    if not to_email or not content:
        return {'success': False, 'error': 'Recipient and content required'}
    
    recipient = find_user_by_email(to_email)
    if not recipient:
        return {'success': False, 'error': 'Recipient not found'}
    
    # Verify they are friends
    are_friends = any(
        f for f in friends 
        if f['user_email'] == from_email and f['friend_email'] == to_email
    )
    
    if not are_friends:
        return {'success': False, 'error': 'You can only message your friends'}
    
    # Create message object
    message = {
        'id': len(messages) + 1,
        'from_email': from_email,
        'to_email': to_email,
        'content': content,
        'timestamp': timestamp,
        'delivered': False
    }
    messages.append(message)
    
    # Check if recipient is online
    if to_email in user_sid_map:
        # Online - deliver immediately
        socketio.emit('new_message', {
            'id': message['id'],
            'from_email': from_email,
            'content': content,
            'timestamp': timestamp
        }, room=user_sid_map[to_email])
        message['delivered'] = True
        delivered = True
        print(f"Delivered message to {to_email} (online)")
    else:
        # Offline - store for later
        delivered = False
        print(f"Stored message for {to_email} (offline)")
    
    return {'success': True, 'message_id': message['id'], 'status': delivered}

# ============ Server Startup ============

if __name__ == '__main__':
    print("=" * 50)
    print("Chat Server Starting")
    print("=" * 50)
    
    socketio.run(app, host='0.0.0.0', port=3000, debug=True)