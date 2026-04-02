from datetime import datetime

class Message:
    SENT = False
    DELIVERED = True
    
    #content: message body, sender, recipent: email, lifetime: seconds
    # TODO complete the class and docs 
    def __init__(self, id: int, content: str, sender: str, recipent: str, delivered: bool, delete_time: datetime | None = None):
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
        self.id = id
        self.message = content
        self.sender = sender
        self.recipent = recipent
        self.delivered = delivered
        self.delete_time = delete_time #time of expiry
    
    def isExpired(self):
        if self.delete_time == None:
            return False  
        return datetime.now() >= self.delete_time
    

        
