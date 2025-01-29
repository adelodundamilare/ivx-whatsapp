
# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.orm import Session
# from datetime import datetime, timedelta
# from app.core.database import get_db
# from app.core.security import create_access_token
# from app.crud.user import user as user_crud
# from app.schemas import auth as auth_schema
# from app.services.email import EmailService
# from app.utils.logger import setup_logger
# from app.services.user import UserService
# from app.services.auth import AuthService
# from app.utils.deps import get_current_user
# from app.models.user import User

# logger = setup_logger("auth_api", "auth.log")

# router = APIRouter()

# user_service = UserService()
# auth_service = AuthService()

# @router.post("/signup")
# async def signup(user_data: auth_schema.UserCreate, db: Session = Depends(get_db)):
#     try:

#         user = user_service.create_user(db, user_data=user_data)
#         verification_code =  auth_service.generate_code()
#         user_service.update_user(db, user, user_data={
#             "verification_code": verification_code,
#             "verification_code_expires_at": datetime.utcnow() + timedelta(minutes=30)
#         })

#         # Send welcome email
#         EmailService.send_email(
#             to_email=user.email,
#             subject="Welcome and Verify Your Account",
#             template_name="welcome-verify.html",
#             template_context={
#                 "name": user.full_name,
#                 "code": verification_code
#             }
#         )

#         return {"message": "User created successfully"}
#     except Exception as e:
#         logger.error(f"Signup failed: {str(e)}")
#         raise

# @router.post("/resend-verification-code")
# async def resend_verification_code(user_data: auth_schema.UserEmail, db: Session = Depends(get_db)):
#     try:
#         user = user_service.find_user_by_email(db, email=user_data.email)
#         verification_code =  auth_service.generate_code()
#         user_service.update_user(db, user, user_data={
#             "verification_code": verification_code,
#             "verification_code_expires_at": datetime.utcnow() + timedelta(minutes=30)
#         })

#         # Send welcome email
#         EmailService.send_email(
#             to_email=user.email,
#             subject="Verify Your Account",
#             template_name="verify-account.html",
#             template_context={
#                 "name": user.full_name,
#                 "code": verification_code
#             }
#         )

#         return {"message": "Verification Code Sent Successfully"}
#     except Exception as e:
#         logger.error(f"Error: {str(e)}")
#         raise

# @router.post("/login/email", response_model=auth_schema.Token)
# async def email_login(user_data: auth_schema.UserLogin, db: Session = Depends(get_db)):
#     try:
#         user = user_service.find_user_by_email(db, email=user_data.email)

#         if not user.is_verified:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Kindly verify account to continue"
#             )

#         if not auth_service.verify_password(user_data.password, user.hashed_password):
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")

#         access_token = create_access_token(data={"sub": user.email})
#         return {"access_token": access_token, "token_type": "bearer"}
#     except Exception as e:
#         logger.error(f"Error: {str(e)}")
#         raise

# @router.post("/verify-email")
# async def email_login(user_data: auth_schema.VerifyEmail, db: Session = Depends(get_db)):
#     try:

#         user = user_service.find_user_by_email(db, email=user_data.email)

#         if user.is_verified:
#            raise HTTPException(
#                status_code=status.HTTP_400_BAD_REQUEST,
#                detail="User email already verified"
#            )

#         if user.verification_code != user_data.verification_code:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Invalid verification code"
#             )

#         if user.verification_code_expires_at < datetime.utcnow():
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Verification code expired"
#             )

#         user_service.update_user(db, user, user_data={
#             "verification_code": None,
#             "verification_code_expires_at": None,
#             "is_verified": True
#         })

#         return {"message": "User Email Verified Successfully"}
#     except Exception as e:
#         logger.error(f"Error: {str(e)}")
#         raise

# @router.post("/login/google", response_model=auth_schema.Token)
# async def google_login(
#     token: str,
#     db: Session = Depends(get_db)
# ):
#     try:
#         user_data = await oauth_service.verify_google_token(token)
#         if not user_data:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Invalid Google token"
#             )

#         user = user_crud.get_by_email(db, email=user_data["email"])
#         if not user:
#             user = user_crud.create(
#                 db,
#                 obj_in=UserCreate(
#                     email=user_data["email"],
#                     full_name=user_data["name"],
#                     auth_provider="google"
#                 )
#             )

#         access_token = create_access_token(data={"sub": user.email})
#         logger.info(f"Google login successful: {user.email}")
#         return {"access_token": access_token, "token_type": "bearer"}
#     except Exception as e:
#         logger.error(f"Google login failed: {str(e)}")
#         raise

# @router.post("/login/apple", response_model=auth_schema.Token)
# async def apple_login(
#     token: str,
#     db: Session = Depends(get_db)
# ):
#     try:
#         user_data = await oauth_service.verify_apple_token(token)
#         if not user_data:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Invalid Apple token"
#             )

#         # Similar implementation as Google login
#         pass
#     except Exception as e:
#         logger.error(f"Apple login failed: {str(e)}")
#         raise


# @router.post("/request-forgot-password")
# async def request_forgot_password(reset_data: auth_schema.UserEmail, db: Session = Depends(get_db)):
#     try:
#         user = user_service.find_user_by_email(db, email=reset_data.email)
#         reset_code = auth_service.request_forget_password(db, user)

#         if not reset_code:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Password reset code not generated"
#             )

#         EmailService.send_email(
#             to_email=user.email,
#             subject="Reset Your Password",
#             template_name="reset_password.html",
#             template_context={
#                 "full_name": user.full_name,
#                 "reset_code": reset_code
#             }
#         )

#         logger.info(f"Password reset code sent to: {user.email}")
#         return {"message": "Reset code sent to email"}
#     except Exception as e:
#         logger.error(f"Password reset failed: {str(e)}")
#         raise

# @router.post("/forgot-password")
# async def forgot_password(reset_data: auth_schema.PasswordResetVerify, db: Session = Depends(get_db)):
#     try:
#         user = user_service.find_user_by_email(db, email=reset_data.email)
#         auth_service.change_password_via_code(db, user, reset_data)

#         EmailService.send_email(
#             to_email=user.email,
#             subject="Password Reset Successfully",
#             template_name="reset-password-success.html",
#             template_context={}
#         )

#         # invalidate token

#         return {"message": "Password Reset Successfully"}
#     except Exception as e:
#         logger.error(f"Error: {str(e)}")
#         raise

# @router.post("/logout")
# async def logout(current_user: User = Depends(get_current_user)):
#    try:
#     #    auth_service.invalidate_token(current_user.id)
#        return {"message": "Logged out successfully"}
#    except Exception as e:
#         logger.error(f"Error: {str(e)}")
#         raise