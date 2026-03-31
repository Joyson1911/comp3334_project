from datetime import datetime, timedelta

class Message:
    
    #content: message body, sender, recipent: email, lifetime: seconds
    # TODO complete the class and docs 
    def __init__(self, content: str, sender: str, recipent: str, creation_time: datetime | None = None, lifetime: int = -1):
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
        self.timestamps = creation_time if creation_time else datetime.now() 
        self.expire_time = (self.timestamps+timedelta(seconds = lifetime)) if lifetime > 0 else None #time of expiry
    
    def isExpired(self):
        if self.expire_time == None:
            return False  
        return datetime.now() >= self.expire_time
    

        