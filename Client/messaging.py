from datetime import datetime

class Message:
    
    def __int__(self, content: str, sender, recipent):
        self.message = content
        self.sender = sender
        self.recipent = recipent
        self.timestamps = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    