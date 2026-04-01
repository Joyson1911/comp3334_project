import socketio
import threading
import time
from typing import Callable

class Client_API:
    """
    Pure WebSocket chat client for real-time messaging application.
    All communication happens through WebSocket connection.
    """
    
    def __init__(self, server_url: str = "http://localhost:3000"):
        """
        Initialize chat client
        
        Args:
            server_url: WebSocket server URL (e.g., http://localhost:3000)
        """
        self.server_url = server_url
        self.sio = socketio.Client()
        self.token = None
        self.user_email = None
        self.is_authenticated = False
        self.is_connected = False
        
        # Callback functions for application layer
        self.on_message = None              # Called when new message received
        self.on_friend_request = None       # Called when friend request received
        self.on_friend_accepted = None      # Called when friend request accepted
        self.on_offline_messages = None     # Called when offline messages received
        self.on_friends_update = None       # Called when friend list updated
        self.on_connected = None            # Called when WebSocket connected
        self.on_disconnected = None         # Called when WebSocket disconnected
        
        # Setup event handlers
        self._setup_handlers()
        
        # Background thread for WebSocket
        self.thread = None
        self.running = False
    
    def _setup_handlers(self):
        """Setup all WebSocket event handlers"""
        
        @self.sio.event
        def connect():
            """Handle successful WebSocket connection"""
            self.is_connected = True
            print("Connected to server")
            if self.on_connected:
                self.on_connected()
        
        @self.sio.event
        def disconnect():
            """Handle WebSocket disconnection"""
            self.is_connected = False
            print("Disconnected from server")
            if self.on_disconnected:
                self.on_disconnected()
        
        @self.sio.on('connected')
        def on_connected(data):
            """Handle connection confirmation from server"""
            print(f"Welcome")
        
        @self.sio.on('new_message')
        def on_new_message(data):
            """Handle incoming real-time message"""
            print(f"Message from {data['from_email']}: {data['content']}")
            if self.on_message:
                self.on_message(data)
        
        @self.sio.on('offline_messages')
        def on_offline_messages(messages):
            """Handle offline messages when user connects"""
            print(f"Received {len(messages)} offline messages")
            if self.on_offline_messages:
                self.on_offline_messages(messages)
            # Also trigger individual message callbacks
            for msg in messages:
                if self.on_message:
                    self.on_message(msg)
        
        @self.sio.on('friend_request_received')
        def on_friend_request(data):
            """Handle incoming friend request"""
            print(f"Friend Request: {data['from_email']} wants to add you as a friend")
            if self.on_friend_request:
                self.on_friend_request(data)
        
        @self.sio.on('friend_request_accepted')
        def on_friend_accepted(data):
            """Handle friend request acceptance notification"""
            print(f"Success: {data['friend_email']} accepted your friend request")
            if self.on_friend_accepted:
                self.on_friend_accepted(data)
        
        @self.sio.on('error')
        def on_error(data):
            """Handle server errors"""
            print(f"Error: {data}")
    
    def connect(self):
        """
        Connect to WebSocket server (non-blocking)
        Starts background thread to handle WebSocket connection
        """
        def connect_thread():
            try:
                self.sio.connect(self.server_url, transports=['websocket'])
                self.sio.wait()  # Block and maintain connection
            except Exception as e:
                print(f"Connection failed: {e}")
                self.is_connected = False
        
        self.thread = threading.Thread(target=connect_thread, daemon=True)
        self.thread.start()
        
        # Wait a moment for connection to establish
        time.sleep(0.5)
    
    def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.is_connected:
            self.sio.disconnect()
            self.is_connected = False
    
    # ============ Authentication Methods ============
    
    def register(self, email: str, password: str, otp: int, callback: Callable = None):
        """
        Register a new user account
        """
        def on_response(data):
            if data.get('success'):
                print(f"Registration successful: {email}")
            else:
                print(f"Registration failed: {data.get('error')}")
            if callback:
                callback(data)
        
        self.sio.on('register_response', on_response)
        self.sio.emit('register', {
            'email': email,
            'password': password,
            'otp': otp
        })
    
    def login(self, email: str, password: str, otp: int, callback: Callable = None):
        """
        Login to existing account
        """
        def on_response(data):
            if data.get('success'):
                self.token = data['access_token']
                self.user_email = email
                self.is_authenticated = True
                print(f"Login successful: {email}")
            else:
                print(f"Login failed: {data.get('error')}")
            if callback:
                callback(data)
        
        self.sio.on('login_response', on_response)
        self.sio.emit('login', {
            'email': email,
            'password': password,
            'otp': otp
        })
    
    def logout(self):
        """Logout from current session"""
        self.sio.emit('logout', {})
        self.token = None
        self.user_email = None
        self.is_authenticated = False
        print("Logged out")
    
    # ============ Friend Management Methods ============
    
    def send_friend_request(self, user_email: str, message: str = "", callback: Callable = None):
        """
        Send friend request to another user
        """
        def on_response(data):
            if data.get('success'):
                print(f"Friend request sent to {user_email}")
            else:
                print(f"Failed to send request: {data.get('error')}")
            if callback:
                callback(data)
        
        self.sio.on('friend_request_response', on_response)
        self.sio.emit('send_friend_request', {
            'user_email': user_email,
            'message': message
        })
    
    def accept_friend_request(self, request_id: int, callback: Callable = None):
        """
        Accept a pending friend request
        """
        def on_response(data):
            if data.get('success'):
                print(f"Friend request accepted")
            else:
                print(f"Failed to accept request: {data.get('error')}")
            if callback:
                callback(data)
        
        self.sio.on('accept_friend_response', on_response)
        self.sio.emit('accept_friend_request', {'request_id': request_id})
    
    # ============ Messaging Methods ============
    
    def send_message(self, to_email: str, content: str, callback: Callable = None):
        """
        Send a message to a friend
        """
        def on_response(data):
            if data.get('success'):
                status = data.get('status', 'unknown')
                if status == 'delivered':
                    print(f"Message delivered to {to_email}")
                elif status == 'stored':
                    print(f"Message stored for {to_email} (offline)")
            else:
                print(f"Failed to send message: {data.get('error')}")
            if callback:
                callback(data)
        
        self.sio.on('message_response', on_response)
        self.sio.emit('send_message', {
            'to_email': to_email,
            'content': content,
            'timestamp': time.time()
        })