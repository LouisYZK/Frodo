from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, SmallInteger, DateTime
from sqlalchemy.orm import relationship

from ext import Base

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(10), unique=True, index=True)
    username = Column(String(10))
    hashed_password = Column(String(100))
    is_active = Column(Boolean, default=True)
    disabled = Column(Boolean, default=False)
    
    items = relationship('Item', back_populates='owner')

class Item(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(20), index=True)
    description = Column(String(20), index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship('User', back_populates='items')

class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100))
    author_id = Column(Integer)
    slug = Column(String(100))
    summary = Column(String(255))
    can_comment = Column(Boolean)
    page_view = Column(Integer)
    status = Column(SmallInteger)
    created_at = Column(DateTime)