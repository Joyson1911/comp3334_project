from cryptography.exceptions import InvalidSignature, InvalidKey
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization as ks, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Self
from enum import Enum

class Padding(Enum):
    OAEP = padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
    PSS = padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH # Use the max available salt length
    )

class RSA():
    """RSA instance for handling the asymmetric key pair operations"""
    
    def __init__(self, pub_key: RSAPublicKey, priv_key: RSAPrivateKey) -> None:
        assert isinstance(pub_key, RSAPublicKey)
        assert isinstance(priv_key, RSAPrivateKey)
        
        self.__public_key = pub_key
        self.__private_key = priv_key
    
    @classmethod
    def create(cls, public_expo: int = 65537, bit_length: int = 1024) -> Self:
        """Creates an RSA encryption instance with given parameters.

        Parameters
        ----------
        public_expo : int, optional
            The public exponent of the key, by default 65537
        bit_length : int, optional
            Expected bit length of the key, longer is better, by default 2048
        """
        return cls(*RSA.__gen_key_pair(public_expo, bit_length))
    
    @classmethod
    def from_str(cls, pub_key_str: str, priv_key_str: str, password: str) -> Self:
        """Creates an RSA instance by the given key string and decryption code.

        Parameters
        ----------
        pub_key_str : str
            PEM public key string.
        priv_key_str : str
            PEM private key string.
        password : str
            Password to decrypt the private key.

        Raises
        ------
        InvalidKey
            If one of the key strings is not a RSA PEM key.
        """
        public_key = RSA.read_pub_key(pub_key_str)
        private_key = ks.load_pem_private_key(priv_key_str.encode(), password.encode())
        if not isinstance(private_key, RSAPrivateKey): 
            raise InvalidKey(f'Private key read is not a RSA private key.')
        return cls(public_key, private_key)
    
    @staticmethod
    def read_pub_key(pub_key_str: str) -> RSAPublicKey:
        """Converts a public key string to RSAPublickey object.

        Parameters
        ----------
        pub_key_str : str
            A PEM public key string.

        Returns
        -------
        RSAPublicKey

        Raises
        ------
        InvalidKey
            If inputted string is not a PEM public key string.
        """
        public_key = ks.load_pem_public_key(pub_key_str.encode())
        if not isinstance(public_key, RSAPublicKey): 
            raise InvalidKey(f'Public key read is not a RSA public key.')
        return public_key
    
    @staticmethod
    def get_pub_str(pub_key: RSAPublicKey) -> str:
        """Gets the public key string in PEM format."""
        return pub_key.public_bytes( 
                    encoding=ks.Encoding.PEM,
                    format=ks.PublicFormat.SubjectPublicKeyInfo
                ).decode()
        
    def pub_key_str(self) -> str:
        """Gets the public key string in PEM format."""
        return RSA.get_pub_str(self.__public_key)
        
    def priv_key_enc_str(self, password: str) -> str:
        """Gets the private ket string in PEM encoded by given password
        
            Note: Password should not be empty.
        """
        return self.__private_key.private_bytes( 
                    encoding=ks.Encoding.PEM,
                    format=ks.PrivateFormat.PKCS8,
                    encryption_algorithm=ks.BestAvailableEncryption(password.encode())
                ).decode()
           
    @staticmethod
    def verify_sign(signature: bytes, message: bytes, other_pub_k: RSAPublicKey) -> bool:
        """Verifies the signature using the given public key.

        Parameters
        ----------
        signature : bytes
            Signature signed with other's private key.
        message : bytes
            Message encrypted by other's private key.

        Returns
        -------
        bool
            `True` if the signed message and the public key belong to the same entity, `False` otherwise.
        """
        try:
            other_pub_k.verify(
                signature,
                message,
                Padding.PSS.value,
                hashes.SHA256()
            )
            return True
        except InvalidSignature:
            return False
    
    def sign_msg(self, message: bytes) -> bytes:
        """Signs a message using self private key.

        Parameters
        ----------
        message : bytes
            Message to be encrypted.

        Returns
        -------
        bytes
            Signature of the signed message.
        """
        return self.__private_key.sign(
            message, 
            Padding.PSS.value,
            hashes.SHA256()
        )
        
    @staticmethod
    def encrypt_msg(message: bytes, other_pub_k: str) -> bytes:
        """Encrypts the message using other's public key.

        Parameters
        ----------
        message : bytes
            Message bytes to be encrypted.
        other_pub_k : RSAPublicKey
            Public key of another entity.

        Returns
        -------
        bytes
            Encrypted bytes.
        """
        
        return RSA.read_pub_key(other_pub_k).encrypt(
            message,
            Padding.OAEP.value,
        )
        
    def decrypt_msg(self, cipher: bytes) -> bytes:
        """Decrypts the cipher by self private key.

        Parameters
        ----------
        cipher : bytes
            Encrypted cipher bytes.

        Returns
        -------
        bytes
            Decrypted message bytes.
        """
        return self.__private_key.decrypt(
            cipher,
            Padding.OAEP.value
        )

    @staticmethod
    def __gen_key_pair(public_expo: int, bit_length: int) -> tuple[RSAPublicKey, RSAPrivateKey]:
        # Generates a pair of public and private key for asymmetric crypting
        priv_k = rsa.generate_private_key(public_expo, bit_length)
        pub_k = priv_k.public_key()
        
        return pub_k, priv_k

import hashlib
import base64

class SHA256:

    """Encapsulation class for SHA-256 hash operations.

    Provides a consistent interface for computing SHA-256 hashes of text or binary data.
    Useful for data integrity verification, token generation, and cryptographic operations.
    """

    def __init__(self, encoding: str = "utf-8"):
        """Initialize the SHA-256 hasher.

        Parameters
        ----------
        encoding: str
            Character encoding for text input, default: utf-8.
        """
        self.encoding = encoding

    def compute(self, data: str | bytes) -> str:
        """Compute SHA-256 hash of the given data.

        Parameters
        ----------
        data: str | bytes 
            String or bytes to hash.

        Returns
        -------
        str
            Hexadecimal string representation of the hash (64 characters).

        Examples
        --------
        >>> hasher = SHA256()
        >>> hasher.compute("hello")
            '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'
        """
        if isinstance(data, str):
            data = data.encode(self.encoding)
        return hashlib.sha256(data).hexdigest()

    def compute_raw(self, data: str | bytes) -> bytes:
        """Compute SHA-256 hash and return raw bytes.

        Parameters
        ----------
        data: str | bytes
            String or bytes to hash.

        Returns
        -------
        bytes
            Raw byte representation of the hash.
        """
        if isinstance(data, str):
            data = data.encode(self.encoding)
        return hashlib.sha256(data).digest()

    def compute_b64(self, data: str | bytes) -> str:
        """Compute SHA-256 hash and return base64-encoded string.

        Parameters
        ----------
        data: str | bytes
            String or bytes to hash.

        Returns
        -------
        str
            Base64-encoded hex string of the hash.
        """
        hash_bytes = self.compute_raw(data)
        return base64.b64encode(hash_bytes).decode("ascii")

    def verify(self, data: str | bytes, expected_hash: str) -> bool:
        """Verify that the data produces the expected hash.

        Parameters
        ----------
        data: str | bytes
            String or bytes to verify.
        expected_hash: str
            Expected hash in hexadecimal format.

        Returns
        -------
        bool
            True if hashes match, False otherwise.
        """
        actual_hash = self.compute(data)
        return actual_hash == expected_hash
    
SALT_LEN = 16

def encrypt_with_pw(text: str, password: str, salt: bytes | None = None) -> bytes:
    """Encrypts a text with provided key and salt shifting, salt show be exactly `crypto.SALT_LEN` long.

    Parameters
    ----------
    text : str
        Text to be encrypted.
    password : str
        Password encrypting the text.
    salt : bytes | None, optional
        The encryption shifting bytes, by default None for auto generation.

    Returns
    -------
    bytes
        Encrypted bytes.
    """
    from os import urandom
    if salt == None:
        salt = urandom(SALT_LEN)
    elif len(salt) < SALT_LEN:
        salt = salt + urandom(SALT_LEN - len(salt))
    elif len(salt) > SALT_LEN:
        salt = salt[:SALT_LEN]
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return salt + Fernet(key).encrypt(text.encode())

def decrypt_with_pw(ciphertext: bytes, password: str) -> str:
    """Decrypts the cipher text with given password.

    Parameters
    ----------
    ciphertext : bytes
        Ciphertext to be decrypt.
    password : str
        Key to decrypt, raises InvalidKey exception if incorrect.
        
    Exceptions:
    InvalidKey
        Raises if provided key is incorrect.

    Returns
    -------
    str
        decrypted message string.
    """
    salt = ciphertext[:SALT_LEN]
    ciphertext = ciphertext[SALT_LEN:]
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    try:
        return Fernet(key).decrypt(ciphertext).decode()
    except Exception:
        raise InvalidKey('The provided password is incorrect.')