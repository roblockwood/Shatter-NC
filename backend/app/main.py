"""Main FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# Import routers
from app.api import machines, status, programs
# from app.api import programs, history

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="CNC Management Platform for Brother CNC Machines",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Include routers
app.include_router(machines.router, prefix="/api/machines", tags=["machines"])
app.include_router(status.router, prefix="/api/machines", tags=["status"])
app.include_router(programs.router, prefix="/api/machines", tags=["programs"])
# app.include_router(programs.router, prefix="/api/programs", tags=["programs"])
# app.include_router(history.router, prefix="/api/history", tags=["history"])


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    # TODO: Initialize database connection pool
    # TODO: Start background polling tasks


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    print(f"Shutting down {settings.APP_NAME}")
    # TODO: Close database connections
    # TODO: Stop background tasks
