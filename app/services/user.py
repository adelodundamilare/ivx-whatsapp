from fastapi import HTTPException, status
from app.crud.user import user as user_crud
from app.core.security import pwd_context

class UserService:
    def create_user(self, db, user_data):
        if user_crud.get_by_email(db, email=user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        return user_crud.create(db, obj_in=user_data)

    def update_user(self, db, user, user_data):
        # should not change email or password
        return user_crud.update(db, db_obj=user, obj_in=user_data)

    def find_user_by_email(self, db, email):
        user = user_crud.get_by_email(db, email=email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user

    def change_password(self, db, user, old_password, new_password):
        if not user_crud.authenticate(db, email=user.email, password=old_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password"
            )

        self.update_user(
            db,
            user,
            {"hashed_password": pwd_context.hash(new_password)}
        )