from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    dictionaries = relationship("Dictionary", back_populates="user", cascade="all, delete-orphan")

class Dictionary(Base):
    __tablename__ = "dictionaries"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="dictionaries")
    words = relationship("SavedWord", back_populates="dictionary", cascade="all, delete-orphan")

class SavedWord(Base):
    __tablename__ = "saved_words"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    dictionary_id = Column(Integer, ForeignKey("dictionaries.id"), nullable=True)
    word = Column(String, index=True, nullable=False)
    definition = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")
    dictionary = relationship("Dictionary", back_populates="words")
