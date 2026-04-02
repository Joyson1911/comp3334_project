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
        id : int
            _description_
        content : str
            _description_
        sender : str
            _description_
        recipent : str
            _description_
        delivered
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
    

        
