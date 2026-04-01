from flask import Flask, request
from flask_socketio import SocketIO, emit, disconnect, ConnectionRefusedError
import secrets
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory storage (replace with database in production !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!)
users = []           # {id, email, password, otp, created_at}
friends = []         # {user_email, friend_email, created_at}
friend_requests = [] # {id, from_email, to_email, status, created_at}
messages = []        # {id, from_email, to_email, content, timestamp, delivered}

# Online user management
online_users = {}    # sid -> user_email
user_sid_map = {}    # user_email -> sid
sessions = {}        # token -> user

# ============ Helper Functions ============

def find_user_by_email(email):
    """Find user by email address"""
    for user in users:
        if user['email'] == email:
            return user
    return None

def generate_token():
    """Generate a secure random token for authentication"""
    return secrets.token_urlsafe(32)

def get_offline_messages(user_email):
    """Retrieve and mark offline messages for a user"""
    undelivered = [m for m in messages 
                   if m['to_email'] == user_email and not m.get('delivered', False)]
    for msg in undelivered:
        msg['delivered'] = True
    return undelivered

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

@socketio.on('register')
def handle_register(data):
    """
    Register a new user account
    Expected data: {email, password, otp}
    """
    email = data.get('email')
    password = data.get('password')
    otp = data.get('otp')
    
    # Validate input
    if not email or not password or not otp:
        emit('register_response', {
            'success': False,
            'error': 'Email, password, and OTP are required'
        })
        return
    
    # Check if email already exists
    if find_user_by_email(email):
        emit('register_response', {
            'success': False,
            'error': 'Email already exists'
        })
        return
    
    # Create new user
    new_user = {
        'id': len(users) + 1,
        'email': email,
        'password': password,
        'otp': otp,
        'created_at': datetime.now().isoformat()
    }
    users.append(new_user)
    
    emit('register_response', {
        'success': True,
        'message': 'User registered successfully',
        'user': {'email': email}
    })

@socketio.on('login')
def handle_login(data):
    """
    Authenticate user and establish session
    Expected data: {email, password, otp}
    """
    email = data.get('email')
    password = data.get('password')
    otp = data.get('otp')
    
    user = find_user_by_email(email)
    
    # Validate credentials
    if not user or user['password'] != password or not otp:
        emit('login_response', {
            'success': False,
            'error': 'Invalid credentials'
        })
        return
    
    # Generate access token
    token = generate_token()
    sessions[token] = user
    
    # Update current connection mapping
    sid = request.sid
    online_users[sid] = email
    user_sid_map[email] = sid
    
    emit('login_response', {
        'success': True,
        'access_token': token,
        'user': {'email': email}
    })
    
    # Send offline messages if any
    offline_msgs = get_offline_messages(user['email'])
    if offline_msgs:
        print(f"Sending {len(offline_msgs)} offline messages to {user['email']}")
        emit('offline_messages', offline_msgs)

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
    Expected data: {user_email, message (optional)}
    """
    sid = request.sid
    if sid not in online_users:
        emit('error', {'error': 'Not authenticated'})
        return
    
    user_email = online_users[sid]
    friend_email = data.get('user_email')
    
    if not friend_email:
        emit('friend_request_response', {'success': False, 'error': 'User email required'})
        return
    
    friend = find_user_by_email(friend_email)
    if not friend:
        emit('friend_request_response', {'success': False, 'error': 'User not found'})
        return
    
    if friend_email == user_email:
        emit('friend_request_response', {'success': False, 'error': 'Cannot add yourself'})
        return
    
    # Check if already friends
    if any(f for f in friends if f['user_email'] == user_email and f['friend_email'] == friend_email):
        emit('friend_request_response', {'success': False, 'error': 'Already friends'})
        return
    
    # Create friend request
    new_request = {
        'id': len(friend_requests) + 1,
        'from_email': user_email,
        'to_email': friend_email,
        'status': 'pending',
        'created_at': datetime.now().isoformat()
    }
    friend_requests.append(new_request)
    
    # Real-time notification if recipient is online
    if friend_email in user_sid_map:
        socketio.emit('friend_request_received', {
            'request_id': new_request['id'],
            'from': user_email,
            'message': data.get('message', '')
        }, room=user_sid_map[friend_email])
    
    emit('friend_request_response', {
        'success': True,
        'message': 'Request sent',
        'request_id': new_request['id']
    })

@socketio.on('accept_friend_request')
def handle_accept_friend_request(data):
    """
    Accept a pending friend request
    Expected data: {request_id}
    """
    sid = request.sid
    if sid not in online_users:
        emit('error', {'error': 'Not authenticated'})
        return
    
    user_email = online_users[sid]
    req_id = data.get('request_id')
    
    # Find the request
    req = next((r for r in friend_requests if r['id'] == req_id), None)
    if not req or req['to_email'] != user_email:
        emit('accept_friend_response', {'success': False, 'error': 'Request not found'})
        return
    
    # Update request status
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
    
    emit('accept_friend_response', {
        'success': True,
        'message': 'Friend request accepted'
    })

# ============ Messaging Events ============

@socketio.on('send_message')
def handle_send_message(data):
    """
    Send a message to a friend
    Expected data: {to, content, timestamp (optional)}
    """
    sid = request.sid
    if sid not in online_users:
        emit('error', {'error': 'Not authenticated'})
        return
    
    from_email = online_users[sid]
    to_email = data.get('to')
    content = data.get('content')
    timestamp = data.get('timestamp', datetime.now().isoformat())
    
    # Validate input
    if not to_email or not content:
        emit('message_response', {'success': False, 'error': 'Recipient and content required'})
        return
    
    recipient = find_user_by_email(to_email)
    if not recipient:
        emit('message_response', {'success': False, 'error': 'Recipient not found'})
        return
    
    # Verify they are friends
    are_friends = any(
        f for f in friends 
        if f['user_email'] == from_email and f['friend_email'] == to_email
    )
    
    if not are_friends:
        emit('message_response', {'success': False, 'error': 'You can only message your friends'})
        return
    
    # Create message object
    message = {
        'id': len(messages) + 1,
        'from': from_email,
        'to': to_email,
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
            'from': from_email,
            'content': content,
            'timestamp': timestamp
        }, room=user_sid_map[to_email])
        message['delivered'] = True
        delivered_status = 'delivered'
        print(f"Delivered message to {to_email} (online)")
    else:
        # Offline - store for later
        delivered_status = 'stored'
        print(f"Stored message for {to_email} (offline)")
    
    emit('message_response', {
        'success': True,
        'message_id': message['id'],
        'status': delivered_status
    })

# ============ Server Startup ============

if __name__ == '__main__':
    print("=" * 50)
    print("Chat Server Starting")
    print("=" * 50)
    print(f"WebSocket endpoint: ws://localhost:3000")
    print(f"Features:")
    print(f"   - User registration/login")
    print(f"   - Friend management")
    print(f"   - Real-time messaging")
    print(f"   - Offline messages")
    print(f"   - Online status tracking")
    print("=" * 50)
    
    socketio.run(app, host='0.0.0.0', port=3000, debug=True)