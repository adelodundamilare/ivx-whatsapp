
from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum

class SubscriptionPlan(str, Enum):
    FREE = "free"
    MONTHLY = "monthly"
    YEARLY = "yearly"

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    subscription_plan: Optional[SubscriptionPlan] = SubscriptionPlan.FREE

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar: Optional[str] = None
    # profession: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    subscription_plan: SubscriptionPlan
    auth_provider: str
    is_verified: bool

    class Config:
        from_attributes = True