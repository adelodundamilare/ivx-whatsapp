
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.endpoints import whatsapp
from fastapi.exceptions import RequestValidationError
from app.middleware.exceptions import global_exception_handler

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for handling WhatsApp messages for anesthesia appointments",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RequestValidationError, global_exception_handler)

# Include routers
# app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(whatsapp.router, prefix="/whatsapp", tags=["whatsapp"])
# app.include_router(utility.router, prefix="/utility", tags=["utility"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)