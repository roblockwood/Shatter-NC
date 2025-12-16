"""Main FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# Import routers
from app.api import machines, status, programs, websocket, history, summary, tools

# Import services
from app.services import WebSocketManager, PollingService

# Global service instances
websocket_manager = WebSocketManager()
polling_service = PollingService(websocket_manager)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="CNC Management Platform for Brother CNC Machines",
)

# Configure CORS
# Handle wildcard origin: if "*" is present, don't use credentials (browser restriction)
# FastAPI's CORSMiddleware requires allow_credentials=False when using ["*"]
cors_origins = settings.CORS_ORIGINS
use_credentials = True
if "*" in cors_origins:
    # When wildcard is used, we can't use credentials - browser security restriction
    # Filter out "*" and use ["*"] explicitly for allow_origins
    use_credentials = False
    processed_origins = ["*"]
else:
    processed_origins = cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=processed_origins,
    allow_credentials=use_credentials,
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
    return {
        "status": "healthy",
        "polling_service": {
            "running": polling_service.is_running,
            "active_machines": len(polling_service.pollers),
            "websocket_connections": websocket_manager.get_connection_count(),
        },
    }


# Include routers
app.include_router(machines.router, prefix="/api/machines", tags=["machines"])
app.include_router(status.router, prefix="/api/machines", tags=["status"])
app.include_router(programs.router, prefix="/api/programs", tags=["programs"])
app.include_router(history.router, prefix="/api", tags=["history"])
app.include_router(summary.router, prefix="/api", tags=["summary"])
app.include_router(tools.router, prefix="/api/tools", tags=["tools"])
app.include_router(websocket.router, prefix="/api", tags=["websocket"])

# Inject websocket manager into websocket router
websocket.set_websocket_manager(websocket_manager)

# Inject polling service into summary router
summary.set_polling_service(polling_service)


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print("Starting background polling service...")
    await polling_service.start()
    print("Polling service started - monitoring all enabled machines")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    print(f"Shutting down {settings.APP_NAME}")
    print("Stopping background polling service...")
    await polling_service.stop()
    print("Polling service stopped")
