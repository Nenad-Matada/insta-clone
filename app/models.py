from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    profile_photo_url = Column(String, nullable=True)  
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    stories = relationship("Story", back_populates="user", cascade="all, delete-orphan")
    followers = relationship("Follow", foreign_keys="Follow.following_id", back_populates="following")
    following = relationship("Follow", foreign_keys="Follow.follower_id", back_populates="follower")

class Story(Base):
    __tablename__ = "stories"
    
    id = Column(Integer, primary_key=True, index=True)
    media_url = Column(String, nullable=False)  
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    close_friends_list = Column(String, nullable=True)  # JSON string or comma-separated IDs
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=datetime.utcnow)  # 24h expiry
    
    user = relationship("User", back_populates="stories")

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    description = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="posts")
    items = relationship("PostItem", back_populates="post", cascade="all, delete-orphan")

class PostItem(Base):
    __tablename__ = "post_items"
    
    id = Column(Integer, primary_key=True, index=True)
    media_url = Column(String, nullable=False)  # URL for photo/video
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    order = Column(Integer, default=0)  # To maintain photo order
    
    post = relationship("Post", back_populates="items")

class Follow(Base):
    __tablename__ = "follows"
    
    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Who follows
    following_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Who is followed
    created_at = Column(DateTime, default=datetime.utcnow)
    
    follower = relationship("User", foreign_keys=[follower_id], back_populates="following")
    following = relationship("User", foreign_keys=[following_id], back_populates="followers")