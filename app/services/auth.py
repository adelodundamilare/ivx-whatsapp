from fastapi import HTTPException, status
import random
import string
from app.services.user import UserService
from datetime import datetime, timedelta
from app.core.security import pwd_context

user_service = UserService()

class AuthService:
    def generate_code(self):
        return ''.join(random.choices(string.digits, k=4))

    def request_forget_password(self, db, user):
        reset_code =  self.generate_code()
        user_service.update_user(db, user, user_data={
            "reset_code": reset_code,
            "reset_code_expires_at": datetime.utcnow()+ timedelta(minutes=30)
        })
        return reset_code

    def change_password_via_code(self, db, user, reset_data):
        if (user.reset_code != reset_data.code or
           user.reset_code_expires_at is None or
           user.reset_code_expires_at < datetime.utcnow()
        ):
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail="Invalid or expired reset code"
           )

        hashed_password = pwd_context.hash(reset_data.new_password)

        user_service.update_user(db, user, {
           "hashed_password": hashed_password,
       })

        user_service.update_user(db, user, {
           "reset_code": None,
           "reset_code_expires_at": None
       })

    def verify_password(self, plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)
