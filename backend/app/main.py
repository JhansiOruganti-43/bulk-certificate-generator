from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import health, batches, certificates, dashboard, auth, me
from app.db.session import engine, Base

# Create tables if they don't exist (basic setup for now)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Global unhandled exception handler to strictly hide stack traces.
# IMPORTANT: HTTPException must be re-raised so FastAPI's built-in handler
# returns the correct 4xx status code (404, 400, etc.) to the client.
# Without this, ALL exceptions including HTTPException would return 500.
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred."}
    )

# Set up CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health.router, prefix="/api")
app.include_router(batches.router, prefix="/api")
app.include_router(certificates.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(me.router, prefix=settings.API_V1_STR, tags=["me"])

@app.get("/")
def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}
