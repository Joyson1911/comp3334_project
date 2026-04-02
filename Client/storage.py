# from cryptography.hazmat.primitives.ciphers.aead import AESGCM
# from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
# from cryptography.exceptions import InvalidTag
from datetime import datetime
import json
from messaging import Message
# from os import urandom, remove, mkdir
from os.path import dirname
from pathlib import Path

from crypto import SHA256, RSA

class SecureStorage:
    CURDIR = Path(__file__).absolute().parent.name
    STORE_DIR = Path(CURDIR).joinpath('save')
    CLIENT_FILE = STORE_DIR.joinpath('client.json')
    
    def __init__(self, email: str):
        """Initiates a SecureStorage instance for managing local secured storage.

        Parameters
        ----------
        email : str
            User email.
        password : str | None, optional
            Password for the user account when registered, by default None if user simply loggin in.
        """
        
        self.email = email
        self.user_msg_dir = ss.STORE_DIR.joinpath(email)
        self.create_if_not_exist(self.user_msg_dir, True)

    def initiated(self) -> bool:
        return ss.CLIENT_FILE.exists()
    
    def load_chat_msg(self, other_email: str) -> list[Message]:
        msg_path = self.user_msg_dir.joinpath(other_email)
        
        messages = []
        
        with msg_path.open('r') as msg_f:
            line = msg_f.readline()
            items = line.split(' ', 4)
            messages.append(MsgStore(
                int(items[0]),
                items[4], 
                bool(int(items[1])), 
                bool(int(items[2])),
                datetime.strptime(items[3], "%d/%m/%Y-%H:%M:%S")
            ).to_Message(self.email, other_email))
            
        return messages
            
    def save_chat_msg(self, other_email: str, messages: list[Message]):
        msg_path = self.user_msg_dir.joinpath(other_email)
        self.create_if_not_exist(msg_path, False)
        
        store_msg = list(map(self.to_msg_store, messages))

        with msg_path.open('w') as msg_f:
            for m in store_msg:
                msg_f.write(str(m) + '\n')
    
    def initiate(self, rsa: RSA, token: str) -> Client:
        ss.create_if_not_exist(ss.CLIENT_FILE, False)
        self.client_info = Client(rsa, token, self.email)
        return self.client_info
        
    def load_client(self) -> Client:
        self.client_info = Client.from_file(ss.CLIENT_FILE)
        return self.client_info
    
    def to_msg_store(self, message: Message) -> MsgStore:
        return MsgStore.from_Message(message, self.email)
        
    @staticmethod
    def create_if_not_exist(filepath: Path, isDir: bool):
        """Creates the target path if provided path not exists and not the correct type.

        Parameters
        ----------
        filepath : str
            Target path.
        isDir : bool
            Whether the expected type of the path is a directory, otherwise a file.
        """
        
        if isDir:
            filepath.mkdir(exist_ok=True)
        else:
            filepath.touch(exist_ok=True)
            
ss = SecureStorage
            
class Client:
    """Store format:  
    \\{  
        "private_key": "",  
        "public_key": "",  
        "session_token": "",  
        "login_email": ""  
    }
    """
    def __init__(self, rsa_instance: RSA, token: str, email: str):
        self.rsa = rsa_instance
        self.token = token
        self.last_email = email
        
    @classmethod
    def from_file(cls, path: Path) -> Client:
        data = json.loads(path.read_text())
        
        token = data['']
        email = data['login_email']
        # assume password is login_email
        password = email
        
        rsa = RSA.from_str(data['public_key'], data['private_key'], password)
        
        return cls(rsa, token, email)
    
    def save(self, path: Path):
        path.write_text(
            json.dumps({
                "private_key": self.rsa.priv_key_enc_str(self.last_email),  
                "public_key": self.rsa.pub_key_str(),  
                "session_token": self.token,  
                "login_email": self.last_email 
            })
        )
             
class MsgStore:
    def __init__(self, id: int, content: str, other_sent: bool, delivered: bool, delete_time: datetime | None): 
        self.id = id
        self.content = content
        self.other_sent = int(other_sent) 
        self.delivered = int(delivered)
        self.delete_time = delete_time
        
    def __str__(self) -> str:
        return f'{self.id} {self.other_sent} '
    
    @classmethod
    def from_Message(cls, msg: Message, self_email: str) -> MsgStore:
        return cls(msg.id, msg.message, msg.sender != self_email, msg.delivered, msg.expire_time)
    
    def to_Message(self, self_email: str, other_email: str) -> Message:
        return Message(self.id, self.content, self_email, other_email, bool(self.delivered), self.delete_time)
        
# def _derive_file_key(self, password: str) -> bytes:
    #     """Derive a 256-bit file encryption key using the Scrypt algorithm."""
    #     # Use a salt for key derivation to prevent rainbow table attacks
    #     salt = b'COMP3334' 
    #     kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    #     return kdf.derive(password.encode())
    
    # def _load_from_disk(self) -> dict:
    #     if not exists(self.user_file) :
    #         # Default structure for a new user
    #         return {
    #             self.user_id: {
    #                 "email": "", 
    #                 "pub_key": "", 
    #                 "priv_key_enc": ""
    #             },
    #             "contacts": {}
    #         }
            
    #     with open(self.filepath, 'rb') as f:
    #         data = f.read()
        
    #     # AES-GCM: First 12 bytes are Nonce, rest is Ciphertext
    #     nonce = data[:12]
    #     ciphertext = data[12:]
        
    #     # Decrypt using the key
    #     aesgcm = AESGCM(self.enc_key)
    #     decrypted = aesgcm.decrypt(nonce, ciphertext, None)
        
    #     # Convert bytes back to a Python Dictionary
    #     return json.loads(decrypted)

    
    # def save(self):
    #     """
    #     Encrypts the current state and persists it to the JSON file.
    #     """
    #     aesgcm = AESGCM(self.enc_key)
    #     nonce = urandom(12) # Fresh nonce for every write operation
    #     json_bytes = json.dumps(self.user_data).encode()
    #     ciphertext = aesgcm.encrypt(nonce, json_bytes, None)
        
    #     with open(self.filepath, 'wb') as f:
    #         f.write(nonce + ciphertext)
    
    # def set_my_profile(self, email: str, pub_key_pem: str, priv_key_enc_pem: str):
    #     """
    #     Updates the user's own identity details.
    #     priv_key_enc_pem is the RSA private key encrypted by crypto.py.
    #     """
    #     self.user_data["me"] = {
    #         "email": email,
    #         "pub_key": pub_key_pem,
    #         "priv_key_enc": priv_key_enc_pem
    #     }
    #     self.save()
        
    # # --- Contact & Session Management (R13, R23, R24) ---
    # def add_or_update_contact(self, email: str, pub_key_pem: str):
    #     """
    #     Adds a contact's public key and generates a Fingerprint.
    #     Utilizes SHA256 from crypto.py for R14 compliance.
    #     """
    #     hasher = SHA256()
    #     # R14: Fingerprint generation using SHA256 hash of the public key
    #     full_hash = hasher.compute(pub_key_pem)
    #     fingerprint = full_hash[:12].upper() # 12-char readable fingerprint
        
    #     if email not in self.user_data["contacts"]:
    #         self.user_data["contacts"][email] = {
    #             "pub_key": pub_key_pem,
    #             "fingerprint": fingerprint,
    #             "unread_count": 0
    #         }
    #     else:
    #         # Update key if contact has performed a key rotation
    #         self.user_data["contacts"][email]["pub_key"] = pub_key_pem
    #         self.user_data["contacts"][email]["fingerprint"] = fingerprint
        
    #     self.save()