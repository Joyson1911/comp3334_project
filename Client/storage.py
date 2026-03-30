import json
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from crypto import SHA256

class SecureStorage:
    
    def __init__(self, filepath, password):
        self.filepath = filepath
        # R4: Derive a 256-bit key from the user's password to encrypt the local JSON file
        self.file_enc_key = self._derive_file_key(password)
        self.data = self._load_from_disk()
       
        
    def _derive_file_key(self, password):
        """Derive a 256-bit file encryption key using the Scrypt algorithm."""
        
        # Use a salt for key derivation to prevent rainbow table attacks
        salt = b'COMP3334' 
        kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
        return kdf.derive(password.encode())
    
    def _load_from_disk(self):
        if not os.path.exists(self.filepath):
            # Default structure for a new user
            return {
                "me": {
                    "email": "", 
                    "pub_key": "", 
                    "priv_key_enc": ""
                },
                "contacts": {}
            }
            
        try:
            with open(self.filepath, 'rb') as f:
                data = f.read()
            
            # AES-GCM: First 12 bytes are Nonce, rest is Ciphertext
            nonce = data[:12]
            ciphertext = data[12:]
            
            # Decrypt using the key
            aesgcm = AESGCM(self.file_enc_key)
            decrypted = aesgcm.decrypt(nonce, ciphertext, None)
            
            #Convert bytes back to a Python Dictionary
            return json.loads(decrypted)
                
        except Exception as e:
            print(f"Storage decryption failed: {e}")
            return None
    
    
    
        
    def save(self):
        """
        Encrypts the current state and persists it to the JSON file.
        """
        aesgcm = AESGCM(self.file_enc_key)
        nonce = os.urandom(12) # Fresh nonce for every write operation
        json_bytes = json.dumps(self.data).encode()
        ciphertext = aesgcm.encrypt(nonce, json_bytes, None)
        
        with open(self.filepath, 'wb') as f:
            f.write(nonce + ciphertext)
    
    def set_my_profile(self, email, pub_key_pem, priv_key_enc_pem):
        """
        Updates the user's own identity details.
        priv_key_enc_pem is the RSA private key encrypted by crypto.py.
        """
        self.data["me"] = {
            "email": email,
            "pub_key": pub_key_pem,
            "priv_key_enc": priv_key_enc_pem
        }
        self.save()
        
    # --- Contact & Session Management (R13, R23, R24) ---
    def add_or_update_contact(self, email, pub_key_pem):
        """
        Adds a contact's public key and generates a Fingerprint.
        Utilizes SHA256 from crypto.py for R14 compliance.
        """
        hasher = SHA256()
        # R14: Fingerprint generation using SHA256 hash of the public key
        full_hash = hasher.compute(pub_key_pem)
        fingerprint = full_hash[:12].upper() # 12-char readable fingerprint
        
        if email not in self.data["contacts"]:
            self.data["contacts"][email] = {
                "pub_key": pub_key_pem,
                "fingerprint": fingerprint,
                "unread_count": 0
            }
        else:
            # Update key if contact has performed a key rotation
            self.data["contacts"][email]["pub_key"] = pub_key_pem
            self.data["contacts"][email]["fingerprint"] = fingerprint
        
        self.save()
    
    
    
    
    def set_unread_count(self, email, count):
        """
        Updates the unread counter (R24) based on server-side push notifications.
        """
        if email in self.data["contacts"]:
            self.data["contacts"][email]["unread_count"] = count
            self.save()

    def reset_unread(self, email):
        """
        Clears the unread counter when the user opens the conversation.
        """
        if email in self.data["contacts"]:
            self.data["contacts"][email]["unread_count"] = 0
            self.save()

    def get_contact_list(self):
        """
        Returns all contact emails for UI rendering.
        """
        return list(self.data["contacts"].keys())

    def get_contact_info(self, email):
        """
        Returns public key and fingerprint for encryption in messaging.py.
        """
        return self.data["contacts"].get(email)