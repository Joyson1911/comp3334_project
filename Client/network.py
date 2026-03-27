import requests
import os
from typing import Dict
import smtplib

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
    
    def emailVerification(verCode: int, receiverMailAddress: str):
        message = "Verification Code: " + verCode
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login("comp3334.project.group60@gmail.com", "nqmx mbam rrhe avyc")
            server.sendmail("comp3334.project.group60@gmail.com", receiverMailAddress, message)
            print("Email sent successfully!")
        except Exception as e:
            print("Error: failed to send verification code")
        finally:
            server.quit()


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
    
    