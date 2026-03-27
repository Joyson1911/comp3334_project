#from __future__ import annotations
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from cryptography.hazmat.primitives import serialization as ks
from math import sqrt
from random import randint
import os.path as path
    
class RSA():
    """RSA instance for handling the asymmetric key pair operations"""
    
    def __init__(self, pub_key: RSAPublicKey, priv_key: RSAPrivateKey) -> None:
        assert isinstance(pub_key, RSAPublicKey)
        assert isinstance(priv_key, RSAPrivateKey)
        
        self.__public_key = pub_key
        self.__private_key = priv_key
    
    @classmethod
    def create(cls, public_expo: int = 65537, bit_length: int = 2048) -> RSA:
        """Creates a RSA encryption instance with given parameters.

        Parameters
        ----------
        public_expo : int, optional
            The public exponent of the key, by default 65537
        bit_length : int, optional
            Expected bit length of the key, longer is better, by default 2048
        """
        return cls(*RSA.__gen_key_pair(public_expo, bit_length))
        
    @classmethod
    def from_file(cls, pub_k_file: str, priv_k_file: str, password: str) -> RSA:
        
        with open(pub_k_file, 'rb') as pub_f:
            
            public_key = ks.load_pem_public_key(pub_f.read())
        with open(priv_k_file, 'rb') as priv_f:
            private_key = ks.load_pem_private_key(priv_f.read(), password.encode())
            
        return cls(public_key, private_key)
        
        
    def save_keys(self, pub_k_file: str, priv_k_file: str, password: str):
        
        pub_k_file = pub_k_file + '.pem' if not pub_k_file.endswith('.pem') else pub_k_file
        priv_k_file = priv_k_file + '.pem' if not priv_k_file.endswith('.pem') else priv_k_file
        
        with open(pub_k_file, 'wb') as pub_f:
            pub_f.write(
                self.__public_key.public_bytes( 
                    encoding=ks.Encoding.PEM,
                    format=ks.PublicFormat.SubjectPublicKeyInfo
                )
            )
        
        with open(priv_k_file, 'wb') as priv_f:
            priv_f.write(
                self.__private_key.private_bytes( 
                    encoding=ks.Encoding.PEM,
                    format=ks.PrivateFormat.PKCS8,
                    encryption_algorithm=ks.BestAvailableEncryption(password.encode())
                )
            )

    @staticmethod
    def __gen_key_pair(public_expo: int, bit_length: int) -> tuple[RSAPublicKey, RSAPrivateKey]:
        priv_k = rsa.generate_private_key(public_expo, bit_length)
        pub_k = priv_k.public_key()
        
        return pub_k, priv_k
        

def is_prime(n: int) -> bool:
    if n <= 1: return False
    if n <= 3: return True
    if n % 2 == 0 or n % 3 == 0: return False
    for i in range(5, int(sqrt(n)) + 1, 6):
        if n % i == 0 or n % (i + 2) == 0: return False
    return True


def is_prime_fast(n: int, k=5) -> bool:
    """Checks where an integere is prime number, using Miller-Rabin primality test. Faster for large integers

    Parameters
    ----------
    n : int
        The integer to be tested
    k : int, optional
        Number of iteration to increase test accuracy, by default 5

    Returns
    -------
    bool
        Whether n is a prime
    """
    
    
    if n <= 1: return False
    if n <= 3: return True
    if n % 2 == 0: return False
    # Factor n-1 as 2^r * d
    r, d = 0, n - 1
    while d % 2 == 0:
        d //= 2
        r += 1
    # Witness loop
    for _ in range(k):
        a = randint(2, n - 2)
        x = pow(a, d, n)
        if x == 1 or x == n - 1: continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1: break
        else: return False # Composite
    return True # Probably prime