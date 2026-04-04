import socketio
import threading
import time
from typing import Callable

class Client_API:
    """
    Pure WebSocket chat client for real-time messaging application.
    All communication happens through WebSocket connection.
    """
    
    def __init__(self, server_url: str = "https://localhost:3000"):
        """
        Initialize chat client
        
        Args:
            server_url: WebSocket server URL (e.g., https://localhost:3000)
        """
        self.server_url = server_url
        self.sio = socketio.Client()
        self.token = None
        self.user_email = None
        self.is_authenticated = False
        self.is_connected = False
        self.receiveBuffer = None
        
        # Callback functions for application layer
        self.on_message = None              # Called when new message received
        self.on_friend_request = None       # Called when friend request received
        self.on_friend_accepted = None      # Called when friend request accepted
        self.on_friend_rejected = None      # Called when friend request rejected
        self.on_offline_messages = None     # Called when offline messages received
        # self.on_friends_update = None       # Called when friend list updated
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
                
        @self.sio.on('friend_request_rejected')
        def on_friend_rejected(data):
            """Handle friend request rejection notification"""
            print(f"Info: rejected your friend request")
            if self.on_friend_rejected:
                self.on_friend_rejected(data)

        @self.sio.on('offline_friend_requests')
        def on_offline_requests(requests):
            print(f"--- Received {len(requests)} offline friend requests ---")
            for req in requests:
                if self.on_friend_request:
                    self.on_friend_request(req)
        
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
    
    # Dont remove !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # def otp_request(self, email: str, action: str, callback: Callable = None):
    #     """
    #     Request OTP for registration or login
    #     """
    #     def on_response(data):
    #         if data.get('success'):
    #             print(f"OTP sent to {email}")
    #         else:
    #             print(f"Failed to send OTP: {data.get('error')}")
    #         if callback:
    #             callback(data)
                
    #     self.sio.emit('otp_request', {
    #         'email': email,
    #         'action': action
    #         }, callback=on_response)
    
    # For testing purposes, return OTP directly !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    def otp_request(self, email: str, action: str):
        try:
            data = self.sio.call('otp_request', {
                'email': email,
                'action': action
            }, timeout=10)

            if data and data.get('success'):
                return {"success": True, "otp": data.get('otp')}
            else:
                return {"success": False, "error": {data.get('error')}}
        except Exception as e:
            return {"success": False, "error": f"Network error: {str(e)}"}
    
    # def register(self, email: str, password: str | None, otp: int | None, callback: Callable = None):
    #     """
    #     Register a new user account
    #     """
    #     def on_response(data):
    #         if data.get('success'):
    #             message = {"success": True}
    #         else:
    #             message = {"success": False, "error": f"Registration failed: {data.get('error')}"}
    #         if callback:
    #             callback(message)
        
    #     self.sio.emit('register', {
    #         'email': email,
    #         'password': password,
    #         'otp': otp,
    #     }, callback=on_response)
    
    def register(self, email: str, password: str, otp: int):
        try:
            data = self.sio.call('register', {
                'email': email,
                'password': password,
                'otp': otp,
            }, timeout=10)

            if data and data.get('success'):
                return {"success": True}
            else:
                return {"success": False, "error": {data.get('error')}}
        except Exception as e:
            return {"success": False, "error": f"Network error: {str(e)}"}
    
    # def login(self, email: str, password: str, otp: int, callback: Callable = None):
    #     """
    #     Login to existing account
    #     """
    #     def on_response(data):
    #         if data.get('success'):
    #             self.token = data['access_token']
    #             self.user_email = email
    #             self.is_authenticated = True
    #             print(f"Login successful: {email}")
    #             print(data.get('friends_list', ["no friends"]))
    #         else:
    #             print(f"Login failed: {data.get('error')}")
    #         if callback:
    #             callback(data)
        
    #     self.sio.emit('login', {
    #         'email': email,
    #         'password': password,
    #         'otp': otp
    #     }, callback=on_response)
    
    def login(self, token: str | None = None, email: str | None = None, password: str | None = None, otp: int | None = None): 
        """
        Login to existing account
        """
        # Can use token instead of email/password/otp for auto-login 
        try:
            data = self.sio.call('login', {
                'token': token,
                'email': email,
                'password': password,
                'otp': otp
            }, timeout=10)
            
            if data and data.get('success'):
                self.token = data['access_token']
                self.user_email = email
                self.is_authenticated = True
                return {"success": True, 
                        "friends_list": data.get('friends_list', []), 
                        "token": self.token, 
                        "token_expiry": data.get('token_expiry')}
            else:
                return {"success": False, "error": f"Login failed: {data.get('error')}"}
        except Exception as e:
            return {"success": False, "error": f"Network error: {str(e)}"}
    
    def logout(self):
        """Logout from current session"""
        self.sio.emit('logout', {})
        self.token = None
        self.user_email = None
        self.is_authenticated = False
        self.receiveBuffer = None
        print("Logged out")
    
    # ============ Friend Management Methods ============
    
    # def send_friend_request(self, user_email: str, message: str = "", callback: Callable = None):
    #     """
    #     Send friend request to another user
    #     """
    #     def on_response(data):
    #         if data.get('success'):
    #             print(f"Friend request sent to {user_email}")
    #         else:
    #             print(f"Failed to send request: {data.get('error')}")
    #         if callback:
    #             callback(data)
        
    #     self.sio.emit('send_friend_request', {
    #         'user_email': user_email,
    #         'message': message
    #     }, callback=on_response)
        
    def send_friend_request(self, user_email: str):
        """ 
        Send friend request to another user
        """
        try:
            data = self.sio.call('send_friend_request', {
                'user_email': user_email,
            }, timeout=10)

            if data and data.get('success'):
                return {"success": True}
            else:
                return {"success": False, "error": f"Failed to send request: {data.get('error')}"}
        except Exception as e:
             return {"success": False, "error": f"Network error: {str(e)}"}
        
    # def respond_to_friend_request(self, request_id, action, callback: Callable =None):
    #     """
    #     Handle a pending friend request (accept or reject)
    #     """
    #     def on_response(data):
    #         if data.get('success'):
    #             print(f"Friend request {action}ed")
    #         else:
    #             print(f"Failed to {action} request: {data.get('error')}")
    #         if callback:
    #             callback(data)
                
    #     self.sio.emit('respond_to_friend_request', {
    #         'request_id': request_id,
    #         'action': action
    #     }, callback=on_response)
        
    def respond_to_friend_request(self, request_id: int, action: str):
        """
        Handle a pending friend request 
        action: "accept" or "reject"
        """
        try:
            data = self.sio.call('respond_to_friend_request', {
                'request_id': request_id,
                'action': action
            }, timeout=10)

            if data and data.get('success'):
                return {"success": True}
            else:
                return {"success": False, "error": f"Failed to {action} request: {data.get('error')}"}
        except Exception as e:
             return {"success": False, "error": f"Network error: {str(e)}"}
         
    def unfriend_request(self, user_email: str, action: str):
        """
        Unfriend user 
        action: "remove" or "block"
        """
        try:
            data = self.sio.call('unfriend_request', {
                'user_email': user_email,
                'action': action
            }, timeout=10)
            
            if action == "remove":
                 if data and data.get('success'):
                    return {"success": True}
                 else:
                    return {"success": False, "error": f"Failed to unfriend: {data.get('error')}"}
            
            if action == "block":
                if data and data.get('success'):
                    return {"success": True, "blocked_list": data.get('blocked_list', [])}
                else:
                    return {"success": False, "error": f"Failed to block user: {data.get('error')}"}
                
        except Exception as e:
             return {"success": False, "error": f"Network error: {str(e)}"}
        
    # ============ Messaging Methods ============
    
    # def send_message(self, to_email: str, content: str, callback: Callable = None):
    #     """
    #     Send a message to a friend
    #     """
    #     def on_response(data):
    #         if data.get('success'):
    #             status = data.get('status', 'unknown')
    #             if status:
    #                 print(f"Message delivered to {to_email}")
    #             else:
    #                 print(f"Message stored for {to_email} (offline)")
    #         else:
    #             print(f"Failed to send message: {data.get('error')}")
    #         if callback:
    #             callback(data)

        # self.sio.emit('send_message', {
        #     'to_email': to_email,
        #     'content': content,
        #     'timestamp': time.time()
        # }, callback=on_response)
        
    def send_message(self, to_email: str, content: str):
        """
        Send a message to a friend
        """
        try:
            data = self.sio.call('send_message', {
                'to_email': to_email,
                'content': content,
                'timestamp': time.time()
            }, timeout=10)

            if data and data.get('success'):
                status = data.get('status', 'unknown')
                if status:
                    return {"success": True, "status": "delivered"}
                else:
                    return {"success": True, "status": "stored"}
            else:
                return {"success": False, "error": f"Failed to send message: {data.get('error')}"}
        except Exception as e:
            return {"success": False, "error": f"Network error: {str(e)}"}