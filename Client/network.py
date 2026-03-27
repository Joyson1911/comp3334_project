import requests
import os
from typing import Optional, Dict, List

class Client_API:
    
    # ============ fundamental functions for API interaction ============
    
    def __init__(self, base_url: str = "https://localhost:8000/api"):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.is_authenticated = False
        
        # Set default headers
        self.session.headers.update({
            'User-Agent': 'comp3334/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })

    def _handle_response(self, response: requests.Response) -> Dict:
        # Handle API response with error checking
        try:
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error {response.status_code}"
            try:
                error_data = response.json()
                error_msg = error_data.get('message', error_msg)
            except:
                pass
            raise Exception(f"{error_msg}: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
        
        


    # ============ register and login ============
    
    def register(self, username: str, email: str, password: str) -> Dict:
        """
        POST /api/register
        Create a new user account
        """
        data = {
            'username': username,
            'email': email,
            'password': password
        }
        
        response = self.session.post(
            f"{self.base_url}/api/register",
            json=data
        )
        
        return self._handle_response(response)
    
    def login(self, username: str, password: str) -> Dict:
        """
        POST /api/login
        Authenticate user and get access token
        """
        data = {
            'username': username,
            'password': password
        }
        
        response = self.session.post(
            f"{self.base_url}/api/login",
            json=data
        )
        
        result = self._handle_response(response)
        
        # Store token for subsequent requests
        if 'access_token' in result:
            self.token = result['access_token']
            self.is_authenticated = True
            self._update_auth_header()
        
        return result
    
    def logout(self) -> Dict:
        """
        POST /api/logout
        Invalidate current session/token
        """
        if not self.is_authenticated:
            raise Exception("Not authenticated")
        
        response = self.session.post(
            f"{self.base_url}/api/logout"
        )
        
        result = self._handle_response(response)
        
        # Clear authentication
        self.token = None
        self.is_authenticated = False
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
        
        return result





    # ============ Friend Management ============
    
    def get_friends(self) -> List[Dict]:
        """
        GET /api/friends
        Get list of user's friends
        """
        if not self.is_authenticated:
            raise Exception("Must be logged in")
        
        response = self.session.get(
            f"{self.base_url}/api/friends"
        )
        
        return self._handle_response(response)
    
    def send_friend_request(self, user_id: int, message: Optional[str] = None) -> Dict:
        """
        POST /api/friend-request
        Send a friend request to another user
        """
        if not self.is_authenticated:
            raise Exception("Must be logged in")
        
        data = {
            'user_id': user_id
        }
        if message:
            data['message'] = message
        
        response = self.session.post(
            f"{self.base_url}/api/friend-request",
            json=data
        )
        
        return self._handle_response(response)
    
    def accept_friend_request(self, request_id: int) -> Dict:
        """
        POST /api/accept-friend
        Accept a pending friend request
        """
        if not self.is_authenticated:
            raise Exception("Must be logged in")
        
        data = {
            'request_id': request_id
        }
        
        response = self.session.post(
            f"{self.base_url}/api/accept-friend",
            json=data
        )
        
        return self._handle_response(response)

    
    
        
    # ============ Messaging ============
    
    def send_message(self, recipient_id: int, content: str, message_type: str = "text") -> Dict:
        """
        POST /api/send-message
        Send a message to a friend
        """
        if not self.is_authenticated:
            raise Exception("Must be logged in")
        
        if not content.strip():
            raise Exception("Message content cannot be empty")
        
        data = {
            'recipient_id': recipient_id,
            'content': content
        }
        
        response = self.session.post(
            f"{self.base_url}/api/send-message",
            json=data
        )
        
        return self._handle_response(response)
    
    def get_offline_messages(self, limit: int = 50) -> List[Dict]:
        """
        GET /api/offline-messages
        Get messages received while offline
        """
        if not self.is_authenticated:
            raise Exception("Must be logged in")
        
        params = {'limit': limit}
        
        response = self.session.get(
            f"{self.base_url}/api/offline-messages",
            params=params
        )
        
        return self._handle_response(response)