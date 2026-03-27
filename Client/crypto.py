import crypto
from typing import Self, ByteString


class Cipher():
    def __init__(self, public_key: num):
        self.code = []
        
        
    @staticmethod
    def encrypt(text: str, public_key: int) -> Self:
        cipher = Cipher()
        