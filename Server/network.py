from flask import Flask, request, jsonify
from functools import wraps
import secrets

app = Flask(__name__)

# In-memory storage
users = []
friends = []
friend_requests = []
messages = []
sessions = {}

# ============ Helper Functions ============

def find_user_by_email(email):
    for user in users:
        if user['email'] == email:
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

# ============ API Endpoints ============

# 1. Register (Removed username)
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    if find_user_by_email(email):
        return jsonify({'error': 'Email already exists'}), 409
    
    new_user = {
        'id': len(users) + 1,
        'email': email,
        'password': password
    }
    
    users.append(new_user)
    return jsonify({
        'message': 'User registered successfully',
        'user': {'email': new_user['email']}
    }), 201

# 2. Login (Uses email instead of username)
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    user = find_user_by_email(email)
    
    if not user or user['password'] != password:  
        return jsonify({'error': 'Invalid credentials'}), 401
    
    token = generate_token()
    sessions[token] = user
    
    return jsonify({
        'message': 'Login successful',
        'access_token': token,
        'user': {'email': user['email']}
    })

# 3. Get friends list
@app.route('/api/friends', methods=['GET'])
@authenticate_token
def get_friends():
    current_user_email = request.user['email']
    user_friends = [f for f in friends if f['user_email'] == current_user_email]
    
    friend_list = []
    for friendship in user_friends:
        friend_list.append({'email': friendship['friend_email']})
    
    return jsonify(friend_list)

# 4. Send friend request
@app.route('/api/friend-request', methods=['POST'])
@authenticate_token
def send_friend_request():
    data = request.get_json()
    friend_email = data.get('user_email')
    
    if not friend_email:
        return jsonify({'error': 'User email is required'}), 400
    
    friend = find_user_by_email(friend_email)
    if not friend:
        return jsonify({'error': 'User not found'}), 404
    
    if friend['email'] == request.user['email']:
        return jsonify({'error': 'Cannot add yourself'}), 400
    
    # Check if already friends
    if any(f for f in friends if f['user_email'] == request.user['email'] and f['friend_email'] == friend_email):
        return jsonify({'error': 'Already friends'}), 400

    new_request = {
        'id': len(friend_requests) + 1,
        'from_user_email': request.user['email'],
        'to_user_email': friend['email'],
        'status': 'pending'
    }
    friend_requests.append(new_request)
    return jsonify({'message': 'Request sent', 'request_id': new_request['id']})

# 5. Accept friend request
@app.route('/api/accept-friend', methods=['POST'])
@authenticate_token
def accept_friend():
    data = request.get_json()
    req_id = data.get('request_id')
    
    req = next((r for r in friend_requests if r['id'] == req_id), None)
    if not req or req['to_user_email'] != request.user['email']:
        return jsonify({'error': 'Request not found'}), 404

    req['status'] = 'accepted'
    friends.append({'user_email': req['from_user_email'], 'friend_email': req['to_user_email']})
    friends.append({'user_email': req['to_user_email'], 'friend_email': req['from_user_email']})
    
    return jsonify({'message': 'Friend accepted'})

# 6. Send Message
@app.route('/api/send-message', methods=['POST'])
@authenticate_token
def send_message():
    data = request.get_json()
    to_email = data.get('to')
    content = data.get('content')
    
    if not to_email or not content:
        return jsonify({'error': 'Recipient and content are required'}), 400
    
    recipient = find_user_by_email(to_email)
    if not recipient:
        return jsonify({'error': 'Recipient not found'}), 404
    
    # Security: Verify they are friends before allowing a message
    are_friends = any(
        f for f in friends 
        if f['user_email'] == request.user['email'] and f['friend_email'] == recipient['email']
    )
    
    if not are_friends:
        return jsonify({'error': 'You can only message your friends'}), 403
    
    new_message = {
        'id': len(messages) + 1,
        'from_email': request.user['email'],
        'to_email': recipient['email'],
        'content': content,
        'timestamp': data.get('timestamp'),
        'delivered': False
    }
    messages.append(new_message)
    
    return jsonify({
        'message': 'Message sent successfully',
        'message_id': new_message['id']
    })

# 7. Get Offline Messages
@app.route('/api/offline-messages', methods=['GET'])
@authenticate_token
def get_offline_messages():
    user_email = request.user['email']
    
    # Filter for undelivered messages sent to this user
    undelivered = [m for m in messages 
                   if m['to_email'] == user_email and not m['delivered']]
    
    # Mark messages as delivered so they don't appear again next time
    for msg in undelivered:
        msg['delivered'] = True
    
    # Format the data to return to the client
    output = []
    for msg in undelivered:
        output.append({
            'id': msg['id'],
            'from': msg['from_email'],
            'content': msg['content'],
            'timestamp': msg['timestamp']
        })
    
    return jsonify(output)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)