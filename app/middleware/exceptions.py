from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

async def global_exception_handler(request: Request, exc: Exception):
    print(f"Unhandled Exception: {exc}")  # Log the full error

    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail}
        )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc)
        }
    )