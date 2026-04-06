from datetime import datetime
import json
from messaging import Message
from typing import Literal, Self
from pathlib import Path
import uuid

from crypto import RSA, RSAPublicKey, encrypt_with_pw, decrypt_with_pw, SHA256
            
class Client:
    """Store format:  
    \\{  
        "private_key": "",  
        "public_key": "",  
        "session_token": "",  
        "login_email": ""  
    }
    """
    def __init__(self, rsa_instance: RSA, token: str | None, email: str | None):
        self.rsa = rsa_instance
        self.token = token
        self.last_email = email
        
    @classmethod
    def from_file(cls, path: Path) -> Self:
        data = json.loads(path.read_text())
        
        token = data['session_token']
        token = None if token == "" else token
        email = data['login_email']
        email = None if email == "" else email
        # assume password is mac address
        password = str(uuid.getnode())
        
        rsa = RSA.from_str(data['public_key'], data['private_key'], password)
        
        return cls(rsa, token, email)
    
    def save(self, path: Path):
        path.write_text(
            json.dumps({
                "private_key": self.rsa.priv_key_enc_str(str(uuid.getnode())),
                "public_key": self.rsa.pub_key_str(),
                "session_token": "" if self.token == None else self.token,
                "login_email": "" if self.last_email == None else self.last_email
            })
        )
             
class MsgStore:
    """Format: {id: int, sent_from: 0/1, status: 0/1, deleteTime: str, content: str}"""
    def __init__(self, id: int, content: str, other_sent: bool, delivered: bool, delete_time: datetime | None): 
        self.id = id
        self.content = content
        self.other_sent = int(other_sent) 
        self.delivered = int(delivered)
        self.delete_time = delete_time
        
    def __str__(self) -> str:
        return f'{self.id} {self.other_sent} {self.delivered} {'-' if self.delete_time == None else self.delete_time.strftime("%d/%m/%Y-%H:%M:%S")} {self.content + '\n'}'
    
    @classmethod
    def from_Message(cls, msg: Message, self_email: str) -> Self:
        return cls(msg.id, msg.message, msg.sender != self_email, msg.delivered, msg.delete_time)
    
    def to_Message(self, self_email: str, other_email: str) -> Message:
        return Message(self.id, self.content, other_email if self.other_sent else self_email, self_email if self.other_sent else other_email, bool(self.delivered), self.delete_time)
        
class SecureStorage:
    CURDIR = Path(__file__).absolute().parent
    STORE_DIR = CURDIR.joinpath('save')
    CLIENT_FILE = STORE_DIR.joinpath('client.json')
        
    def set_email(self, email: str):
        """Sets the email to be managed.

        Parameters
        ----------
        email : str
            Email to be managed.
        """
        self.email = email
        self.user_msg_dir = ss.STORE_DIR.joinpath(email)
        self.create_if_not_exist(self.user_msg_dir, True)
        self.enc_pw = str(uuid.getnode()) + email
    
    def initiate(self, salt: str = 'COMP3334'):
        """Initiate the security storage, the client info of the device. 

        Parameters
        ----------
        rsa : RSA
            RSA instance containing device public and private key (identity key pair).
        token : str
            Available session token.
        """
        if not ss.CLIENT_FILE.exists():
            ss.create_if_not_exist(ss.CLIENT_FILE, False)
            self.client_info = Client(RSA.create(), None, None)
            self.save_client_info()
        else:
            self._load_client()
            
        self.salt = SHA256().compute('salt').encode()
            
    def get_unread_count(self, other_email: str) -> int:
        msg_path = list(self.user_msg_dir.glob(f'{other_email}_*'))
        
        if len(msg_path) <= 0: return 0
        
        msg_path = msg_path[0]
        return int(msg_path.stem.split('_')[-1])
    
    def set_unread_count(self, other_email: str, count: int):
        msg_path = list(self.user_msg_dir.glob(f'{other_email}_*'))
        
        if len(msg_path) <= 0:
            self.user_msg_dir.joinpath(f'{other_email}_{count}.txt').touch()
        else:
            msg_path[0].rename(self.user_msg_dir.joinpath(f'{other_email}_{count}.txt'))
        
    def load_chat_msg(self, other_email: str) -> list[Message]:
        """Loads all the messages of chat between self and other, returns empty list if no messages in the conversation.

        Parameters
        ----------
        other_email : str
            Email owned by the entity that is chatting with self.

        Returns
        -------
        list[Message]
            A list of all chat room messages.
        """
        msg_path = list(self.user_msg_dir.glob(f'{other_email}_*'))
        
        if len(msg_path) <= 0: return []
        
        messages = []
        with msg_path[0].open('rb') as msg_f:
            for line in msg_f.readlines():
                if line == b'': continue
                line = decrypt_with_pw(line, self.enc_pw)
                items = line.split(' ', 4)
                messages.append(MsgStore(
                    int(items[0]),
                    items[4].strip('\n'), 
                    bool(int(items[1])), 
                    bool(int(items[2])),
                    None if items[3] == '-' else datetime.strptime(items[3], "%d/%m/%Y-%H:%M:%S")
                ).to_Message(self.email, other_email))
        return messages
    
    def write_chat_msg(self, other_email: str, messages: list[Message], mode: Literal['a', 'w'] = 'w'):
        """Saves the chat message into corresponding storage space.

        Parameters
        ----------
        other_email : str
            Email which is in conversation with self.
        messages : Message
            Message will be prepend to the first line.
        """
        msg_path = list(self.user_msg_dir.glob(f'{other_email}_*'))
        
        if len(msg_path) <= 0:
            f = self.user_msg_dir.joinpath(f'{other_email}_0.txt')
            f.touch()
            msg_path.append(f)
        
        store_msg = list(map(lambda m: str(self._to_msg_store(m)), messages))

        with msg_path[0].open(f'{mode}b') as msg_f:
            for m in store_msg:
                msg_f.write(encrypt_with_pw(m, self.enc_pw, self.salt))
            
    def append_msgs(self, email: str, msg_list: list[Message]):
        self.write_chat_msg(email, msg_list, 'a')
            
    def remove_session(self):
        """Removes the current session"""
        self.client_info.token = None
        self.client_info.last_email = None
    
    def update_session(self, new_token: str, email: str):
        """Updates the session of loggin user. 

        Parameters
        ----------
        new_token : str
            New session token for current logged in user.
        email : str
            Email of the new user owning the session.
        """
        self.set_email(email)
        self.client_info.token = new_token
        self.client_info.last_email = email
        
    def save_client_info(self):
        """Saves the current client_info, with updated session and corresponding email."""
        self.client_info.save(ss.CLIENT_FILE)
        
    def _load_client(self):
        self.client_info = Client.from_file(ss.CLIENT_FILE)

    def _to_msg_store(self, message: Message) -> MsgStore:
        return MsgStore.from_Message(message, self.email)
    
    @staticmethod
    def get_public_key(other_email: str) -> RSAPublicKey | None:
        key_path = ss.STORE_DIR.joinpath(other_email, 'k.pem')
        
        if not key_path.exists():
            return None
        
        with key_path.open('r') as f:
            return RSA.read_pub_key(f.read())
        
    @staticmethod
    def save_public_key(other_email: str, pub_key: RSAPublicKey):
        key_path = ss.STORE_DIR.joinpath(other_email, 'k.pem')
        ss.create_if_not_exist(key_path, False)
        
        with key_path.open('w') as f:
            f.write(RSA.get_pub_str(pub_key))
        
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
            filepath.mkdir(exist_ok=True, parents=True)
        else:
            filepath.parent.mkdir(exist_ok=True, parents=True)
            filepath.touch(exist_ok=True)
            
ss = SecureStorage        
        
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