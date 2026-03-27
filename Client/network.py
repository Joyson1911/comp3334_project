import requests
import os
from typing import Dict

class Client_API:
    
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

