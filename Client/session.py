import uuid
from typing import List

def getMacAddress():
        mac = uuid.getnode()
        mac_address = ':'.join([f'{(mac >> ele) & 0xff:02x}' for ele in range(40, -1, -8)])
        return mac_address

class Account:
    
    def __init__(self, user: str, publicKey: str, privateKey: str, friends: List[str], unread: list[int], blacklist: List[str], sent: List[str], received: List[str]):
        self.user = user
        self.friendlist = {"friends": friends, "unread": unread}
        self.blacklist = blacklist
        self.request = {"sent": sent, "received": received}
        self.publicKey = publicKey
        self.privateKey = privateKey    

    def addFriend(self, index):
        self.friendlist["friends"].append(self.request["received"][index])
        self.friendlist["unread"].append(0)

    def removeFriend(self, index):
        self.friendlist["friends"].pop(index)
        self.friendlist["unread"].pop(index)

    def blacklistUser(self, userEmail):
        if userEmail in self.friendlist["friends"]:
             self.removeFriend(self.friendlist["friends"].index(userEmail))
        self.blacklist.append(userEmail)

class Recipient():

    def __init__(self, email: str, publicKey: str, macAddress: str, messages: List):
        self.email = email
        self.publicKey = publicKey
        self.macAddress = macAddress
        self.messages = messages #message