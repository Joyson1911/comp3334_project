from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    # otp = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    macAddress = db.Column(db.String(50))
    publicKey = db.Column(db.Text)
    
class Friendship(db.Model):
    __tablename__ = 'friendships'
    user_email = db.Column(db.String(120), primary_key=True)
    friend_email = db.Column(db.String(120), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
class BlockedUser(db.Model):
    __tablename__ = 'blocked_users'
    user_email = db.Column(db.String(120), primary_key=True)
    blocked_email = db.Column(db.String(120), primary_key=True)
    
class FriendRequest(db.Model):
    __tablename__ = 'friend_requests'
    from_email = db.Column(db.String(120), primary_key=True)
    to_email = db.Column(db.String(120), primary_key=True)
    status = db.Column(db.String(20), default='pending') # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    from_email = db.Column(db.String(120), nullable=False)
    to_email = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    delivered = db.Column(db.Boolean, default=False)
    macAddress = db.Column(db.String(50))
    del_time = db.Column(db.String(50))  