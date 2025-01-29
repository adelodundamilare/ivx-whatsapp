
# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.orm import Session
# from app.core.database import get_db
# from app.crud.user import user as user_crud
# from app.schemas import user as user_schema
# from app.utils.deps import get_current_user
# from app.utils.logger import setup_logger
# from app.models.user import User
# from app.services.email import EmailService
# from app.services.user import UserService

# logger = setup_logger("account_api", "account.log")

# router = APIRouter()
# user_service = UserService()

# @router.get("/me", response_model=user_schema.UserResponse)
# async def get_profile(
#     current_user: User = Depends(get_current_user)
# ):
#     try:
#         return current_user
#     except Exception as e:
#         logger.error(f"Error: {str(e)}")
#         raise

# @router.put("/me", response_model=user_schema.UserResponse)
# async def update_profile(
#     user_update: user_schema.UserUpdate,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     try:
#         updated_user = user_service.update_user(db, current_user, user_update)
#         return updated_user
#     except Exception as e:
#         logger.error(f"Error: {str(e)}")
#         raise

# @router.post("/me/change-password")
# async def change_password(
#     old_password: str,
#     new_password: str,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     try:
#         user_service.change_password(db, current_user, old_password, new_password)

#         EmailService.send_email(
#             to_email=current_user.email,
#             subject="Password Reset Successfully",
#             template_name="reset-password-success.html",
#             template_context={}
#         )

#         # log out
#         logger.info(f"Password changed for user: {current_user.email}")
#         return {"message": "Password updated successfully"}
#     except Exception as e:
#         logger.error(f"Error: {str(e)}")
#         raise

# @router.delete("/me")
# async def delete_account(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     try:
#         user_crud.delete(db, id=current_user.id)
#         logger.info(f"Account deleted: {current_user.email}")
#         return {"message": "Account deleted successfully"}
#     except Exception as e:
#         logger.error(f"Error: {str(e)}")
#         raise