#from __future__ import annotations
from cryptography.hazmat.primitives.asymmetric import rsa, padding, types
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from cryptography.hazmat.primitives import serialization as ks, hashes
from cryptography.exceptions import InvalidSignature, InvalidKey
from math import sqrt
from random import randint
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
    def create(cls, public_expo: int = 65537, bit_length: int = 2048) -> RSA:
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
    def from_str(cls, pub_key_str: str, priv_key_str: str, password: str) -> RSA:
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
        public_key = ks.load_pem_public_key(pub_key_str.encode())
        private_key = ks.load_pem_private_key(priv_key_str.encode(), password.encode())
        if not isinstance(public_key, RSAPublicKey): 
            raise InvalidKey(f'Public key read is not a RSA public key.')
        if not isinstance(private_key, RSAPrivateKey): 
            raise InvalidKey(f'Private key read is not a RSA private key.')
        return cls(public_key, private_key)
        
    def pub_key_str(self) -> str:
        """Gets the public key string in PEM format."""
        return self.__public_key.public_bytes( 
                    encoding=ks.Encoding.PEM,
                    format=ks.PublicFormat.SubjectPublicKeyInfo
                ).decode()
        
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
    def encrypt_msg(message: bytes, other_pub_k: RSAPublicKey) -> bytes:
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
        return other_pub_k.encrypt(
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