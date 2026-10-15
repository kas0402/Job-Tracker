from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    applications = relationship("Application", back_populates="owner")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    company = Column(String, nullable=False)
    role = Column(String, nullable=False)
    link = Column(String)
    salary = Column(Integer)
    status = Column(String, default="saved", index=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="applications")
    history = relationship(
        "StatusHistory",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="StatusHistory.changed_at",
    )

class StatusHistory(Base):
    __tablename__ = "status_history"

    id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer, ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    old_status = Column(String)
    new_status = Column(String, nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", back_populates="history")