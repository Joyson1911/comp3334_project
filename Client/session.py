import uuid

def getMacAddress():
        mac = uuid.getnode()
        mac_address = ':'.join([f'{(mac >> ele) & 0xff:02x}' for ele in range(40, -1, -8)])
        return mac_address

class Status:
    
    def __init__(self, sender: str, publicKey: str, privateKey: str):
        self.sender = sender
        self.friends = []
        self.blacklist = []
        self.publicKey = publicKey
        self.privateKey = privateKey
        self.macAddress = getMacAddress()
    

class Recipient():

    def __init__(self, email: str, publicKey: str, macAddress: str, messages):
        self.email = email
        self.publicKey = publicKey
        self.macAddress = macAddress
        self.messages = messages #message