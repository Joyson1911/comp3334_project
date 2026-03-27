"""
sender "POST   /api/register
POST   /api/login
POST   /api/logout
GET    /api/friends
POST   /api/friend-request
POST   /api/accept-friend
POST   /api/send-message
GET    /api/offline-messages"
client --> api --> server
'User-Agent': 'comp3334/1.0',
'Accept': 'application/json',
'Content-Type': 'application/json'
data: json
"""
from flask import Flask, request, jsonify
from functools import wraps
import secrets
import json


app = Flask(__name__)

# In-memory storage (replace with database in production)
users = []
friends = []
friend_requests = []
messages = []
sessions = {}

# Helper functions
def find_user_by_username(username):
    for user in users:
        if user['username'] == username:
            return user
    return None


def find_user_by_email(email):
    for user in users:
        if user['email'] == email:
            return user
    return None

def find_user_by_id(user_id):
    for user in users:
        if user['id'] == user_id:
            return user
    return None

def generate_token():
    return secrets.token_urlsafe(32)

def authenticate_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else None
        
        if not token or token not in sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        
        request.user = sessions[token]
        return f(*args, **kwargs)
    return decorated

@app.after_request
def add_headers(response):
    response.headers['User-Agent'] = 'comp3334/1.0'
    response.headers['Accept'] = 'application/json'
    response.headers['Content-Type'] = 'application/json'
    return response

# 1. Register
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not username or not email or not password:
        return jsonify({'error': 'All fields are required'}), 400
    
    if find_user_by_username(username):
        return jsonify({'error': 'Username already exists'}), 409
    
    if find_user_by_email(email):
        return jsonify({'error': 'Email already exists'}), 409
    
    new_user = {
        'id': len(users) + 1,
        'username': username,
        'email': email,
        'password': password
    }
    
    users.append(new_user)
    
    return jsonify({
        'message': 'User registered successfully',
        'user': {
            'id': new_user['id'],
            'username': new_user['username'],
            'email': new_user['email']
        }
    }), 201


# 2. Login
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    user = find_user_by_username(username)
    
    if not user or user['password'] != password:  
        return jsonify({'error': 'Invalid credentials'}), 401
    
    token = generate_token()
    sessions[token] = user
    
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email']
        }
    })

# 3. Logout
@app.route('/api/logout', methods=['POST'])
@authenticate_token
def logout():
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else None
    
    if token and token in sessions:
        del sessions[token]
    
    return jsonify({'message': 'Logout successful'})

# 4. Get friends list
@app.route('/api/friends', methods=['GET'])
@authenticate_token
def get_friends():
    user = request.user
    user_friends = [f for f in friends if f['user_id'] == user['id']]
    
    friend_list = []
    for friendship in user_friends:
        friend = find_user_by_id(friendship['friend_id'])
        if friend:
            friend_list.append({
                'id': friend['id'],
                'username': friend['username'],
                'email': friend['email']
            })
    
    return jsonify({'friends': friend_list})

# 5. Send friend request
@app.route('/api/friend-request', methods=['POST'])
@authenticate_token
def send_friend_request():
    data = request.get_json()
    friend_username = data.get('username')
    
    if not friend_username:
        return jsonify({'error': 'Username is required'}), 400
    
    friend = find_user_by_username(friend_username)
    
    if not friend:
        return jsonify({'error': 'User not found'}), 404
    
    if friend['id'] == request.user['id']:
        return jsonify({'error': 'Cannot send friend request to yourself'}), 400
    
    # Check if request already exists
    existing_request = next(
        (r for r in friend_requests 
         if r['from_user_id'] == request.user['id'] 
         and r['to_user_id'] == friend['id'] 
         and r['status'] == 'pending'),
        None
    )
    
    if existing_request:
        return jsonify({'error': 'Friend request already sent'}), 400
    
    # Check if already friends
    already_friends = any(
        f for f in friends 
        if (f['user_id'] == request.user['id'] and f['friend_id'] == friend['id'])
        or (f['user_id'] == friend['id'] and f['friend_id'] == request.user['id'])
    )
    
    if already_friends:
        return jsonify({'error': 'Already friends'}), 400
    
    friend_request = {
        'id': len(friend_requests) + 1,
        'from_user_id': request.user['id'],
        'to_user_id': friend['id'],
        'status': 'pending'
    }
    
    friend_requests.append(friend_request)
    
    return jsonify({
        'message': 'Friend request sent',
        'request_id': friend_request['id']
    })

# 6. Accept friend request
@app.route('/api/accept-friend', methods=['POST'])
@authenticate_token
def accept_friend():
    data = request.get_json()
    request_id = data.get('request_id')
    
    if not request_id:
        return jsonify({'error': 'Request ID is required'}), 400
    
    friend_request = next(
        (r for r in friend_requests if r['id'] == request_id),
        None
    )
    
    if not friend_request:
        return jsonify({'error': 'Friend request not found'}), 404
    
    if friend_request['to_user_id'] != request.user['id']:
        return jsonify({'error': 'Not authorized to accept this request'}), 403
    
    if friend_request['status'] != 'pending':
        return jsonify({'error': 'Friend request already processed'}), 400
    
    # Update request status
    friend_request['status'] = 'accepted'
    
    # Add to friends list
    friends.append({
        'user_id': friend_request['from_user_id'],
        'friend_id': friend_request['to_user_id']
    })
    
    return jsonify({'message': 'Friend request accepted'})

# 7. Send message
@app.route('/api/send-message', methods=['POST'])
@authenticate_token
def send_message():
    data = request.get_json()
    to_username = data.get('to')
    content = data.get('content')
    
    if not to_username or not content:
        return jsonify({'error': 'Recipient and content are required'}), 400
    
    recipient = find_user_by_username(to_username)
    
    if not recipient:
        return jsonify({'error': 'Recipient not found'}), 404
    
    # Check if they are friends
    are_friends = any(
        f for f in friends 
        if (f['user_id'] == request.user['id'] and f['friend_id'] == recipient['id'])
        or (f['user_id'] == recipient['id'] and f['friend_id'] == request.user['id'])
    )
    
    if not are_friends:
        return jsonify({'error': 'Can only send messages to friends'}), 403
    
    message = {
        'id': len(messages) + 1,
        'from_user_id': request.user['id'],
        'to_user_id': recipient['id'],
        'content': content,
        'timestamp': str(__import__('datetime').datetime.now()),
        'delivered': False
    }
    
    messages.append(message)
    
    return jsonify({
        'message': 'Message sent',
        'message_id': message['id']
    })

# 8. Get offline messages
@app.route('/api/offline-messages', methods=['GET'])
@authenticate_token
def get_offline_messages():
    user = request.user
    
    # Get undelivered messages for this user
    undelivered = [m for m in messages 
                   if m['to_user_id'] == user['id'] and not m['delivered']]
    
    # Mark as delivered
    for msg in undelivered:
        msg['delivered'] = True
    
    # Format messages for response
    message_list = []
    for msg in undelivered:
        sender = find_user_by_id(msg['from_user_id'])
        message_list.append({
            'id': msg['id'],
            'from': sender['username'] if sender else 'Unknown',
            'content': msg['content'],
            'timestamp': msg['timestamp']
        })
    
    return jsonify({'messages': message_list})

# Error handler for 404
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

# Error handler for 500
@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)