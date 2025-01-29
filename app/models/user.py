from sqlalchemy import Boolean, Column, String, Integer, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    avatar = Column(String, nullable=True)
    is_active = Column(Boolean(), default=True)
    is_verified = Column(Boolean(), default=False)
    subscription_plan = Column(String, default="free")  # free, monthly, yearly
    auth_provider = Column(String, default="email")  # email, google, apple
    reset_code = Column(String, nullable=True)
    reset_code_expires_at = Column(DateTime, nullable=True)
    verification_code = Column(String, nullable=True)
    verification_code_expires_at = Column(DateTime, nullable=True)
    is_verified = Column(Boolean(), default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())