import uuid
from typing import List
from storage import SecureStorage

def getMacAddress():
        mac = uuid.getnode()
        mac_address = ':'.join([f'{(mac >> ele) & 0xff:02x}' for ele in range(40, -1, -8)])
        return mac_address

class Account:
    
    def __init__(self, user: str, friends: List[str], unread: list[int], blacklist: List[str], sent: List[str], received: List[str], token: str):
        self.locked = False
        self.user = user
        self.friendlist = {"friends": friends, "unread": unread}
        self.blacklist = blacklist
        self.request = {"sent": sent, "received": received} 
        self.token = token

    def buildAccount(email: str, storage: SecureStorage):
        friends = []
        unread = []
        blacklist = []
        sent = []
        received = []

        for frd in friends:
            unread.append(storage.get_unread_count(frd))

        account = Account()
        ...

    def lock(self):
         while self.locked:
            pass
         self.locked = True

    def unlock(self):
        self.locked = False

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