from app.core.config import settings
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
)

class CloudinaryService:

    def upload_file(self, file: bytes):
        result = cloudinary.uploader.upload(file)
        return result["secure_url"]

