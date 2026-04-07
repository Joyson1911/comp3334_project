import uuid
from typing import List
from storage import SecureStorage

def getMacAddress():
        mac = uuid.getnode()
        mac_address = ':'.join([f'{(mac >> ele) & 0xff:02x}' for ele in range(40, -1, -8)])
        return mac_address

class Account:
    
    def __init__(self, user: str, friends: List[str], unread: list[int], blacklist: List[str], token: str, sent: List[str] = [], received: List[str] = []):
        self.locked = False
        self.user = user
        self.friendlist = {"friends": friends, "unread": unread}
        self.blacklist = blacklist
        self.request = {"sent": sent, "received": received} 
        self.token = token
        self.receiveBuffer = []

    def lock(self):
         while self.locked:
            pass
         self.locked = True

    def unlock(self):
        self.locked = False

    def addFriend(self, user: str, request: str):
        #Request: "sent"/"received"
        self.lock()
        index = self.request[request].index(user)
        self.friendlist["friends"].append(self.request[request][index])
        self.friendlist["unread"].append(0)
        self.unlock()

    def removeFriend(self, user):
        self.lock()
        index = self.friendlist["friends"].index(user)
        self.friendlist["friends"].pop(index)
        self.friendlist["unread"].pop(index)
        self.unlock()
    
    def addSentRequest(self, receiver: str):
        self.lock()
        self.request["sent"].append(receiver)
        self.unlock()

    def removeSentRequest(self, receiver: str):
        self.lock()
        self.request["sent"].remove(receiver)
        self.unlock()

    def addRcvdRequest(self, sender: str):
        self.lock()
        self.request["received"].append(sender)
        self.unlock()

    def removeRcvdRequest(self, sender: str):
        self.lock()
        self.request["received"].remove(sender)
        self.unlock()

    def blacklistUser(self, userEmail):
        if userEmail in self.friendlist["friends"]:
             self.removeFriend(self.friendlist["friends"].index(userEmail))
        self.blacklist.append(userEmail)

    def clearUnread(self, userEmail):
        self.lock()
        self.friendlist["unread"][self.friendlist["friends"].index(userEmail)]=0
        self.unlock()

    def moveToFront(self, userEmail):
        self.lock()
        index = self.friendlist["friends"].index(userEmail)
        friend = self.friendlist["friends"][index]
        unread = self.friendlist["unread"][index]
        del self.friendlist["friends"][index]
        del self.friendlist["unread"][index]
        self.friendlist["friends"].insert(0, friend)
        self.friendlist["unread"].insert(0, unread)
        self.unlock()

    def unreadIncrement(self, userEmail):
        self.lock()
        self.friendlist["unread"][self.friendlist["friends"].index(userEmail)] +=1
        self.unlock()