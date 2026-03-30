from datetime import datetime, timedelta

class Message:
    
    #content: message body, sender, recipent: email, lifetime: seconds
    def __init__(self, content: str, sender: str, recipent: str, lifetime: int = None):
        self.message = content
        self.sender = sender
        self.recipent = recipent
        self.timestamps = datetime.now() #time of creation
        self.expiry= lifetime == None if lifetime == None else (self.timestamps+self.timestamps(seconds = lifetime))#time of expiry
    
    def isExpired(self):
        if self.lifetime == None:
            return False  
        return datetime.now()>=self.expiry
    

        