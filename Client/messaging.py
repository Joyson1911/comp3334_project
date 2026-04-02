from datetime import datetime, timedelta

class Message:
    SENT = False
    DELIVERED = True
    
    #content: message body, sender, recipent: email, lifetime: seconds
    # TODO complete the class and docs 
    def __init__(self, content: str, sender: str, recipent: str, lifetime: int = -1, status: bool = None):
        """Construct a message object by the given args

        Parameters
        ----------
        content : str
            _description_
        sender : str
            _description_
        recipent : str
            _description_
        creation_time : datetime | None, optional
            The time the message is created, by default None for the instant time the class is created.
            Note that messages could be sent by others and are created before receiving.
        lifetime : int, optional
            The message life time in seconds before it is detroyed, by default -1 for lasting forever.
        """
        self.message = content
        self.sender = sender
        self.recipent = recipent
        # time of creation
        self.deleteTime = -1 if lifetime==-1 else datetime.now() + timedelta(seconds=lifetime)
        self.status = status
    
    def isExpired(self):
        if self.expire_time == None:
            return False  
        return datetime.now() >= self.deleteTime