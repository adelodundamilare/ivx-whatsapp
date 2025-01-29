from pydantic import BaseModel, EmailStr
from typing import Optional

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    # refresh_token: str

class PasswordResetVerify(BaseModel):
    email: EmailStr
    code: str
    new_password: str

class UserEmail(BaseModel):
    email: EmailStr

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class VerifyEmail(BaseModel):
    email: EmailStr
    verification_code: str
