
# from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
# from sqlalchemy.orm import Session
# from app.core.database import get_db
# from app.crud.user import user as user_crud
# from app.schemas import user as user_schema
# from app.utils.deps import get_current_user
# from app.utils.logger import setup_logger
# from app.models.user import User
# from app.services.email import EmailService
# from app.services.user import UserService
# from app.services.cloudinary import CloudinaryService

# logger = setup_logger("utility_api", "utility.log")

# router = APIRouter()
# user_service = UserService()
# cloudinary_service = CloudinaryService()

# @router.post("/upload-to-cloud")
# async def upload_to_cloud(
#     file: UploadFile = File(...)
#     # current_user: User = Depends(get_current_user),
#     # db: Session = Depends(get_db)
# ):
#     try:
#         file_bytes = await file.read()
#         res = cloudinary_service.upload_file(file_bytes)
#         return {"message": "File uploaded successfully", "url": res}
#     except Exception as e:
#         logger.error(f"Error: {str(e)}")
#         raise
