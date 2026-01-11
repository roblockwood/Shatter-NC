"""Main FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
import logging

# Configure logging level from settings
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Import routers
from app.api import machines, status, programs, websocket, history, summary, tools
from app.api import settings as settings_api

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

# Debug: Log CORS configuration
print(f"CORS_ORIGINS from settings: {cors_origins}")
print(f"CORS_ORIGINS type: {type(cors_origins)}")

# Check if wildcard is in the list (handle both string and list formats)
has_wildcard = False
if isinstance(cors_origins, list):
    has_wildcard = "*" in cors_origins
elif isinstance(cors_origins, str):
    # Handle case where it might be a string representation
    has_wildcard = "*" in cors_origins or cors_origins == "*"

if has_wildcard:
    # When wildcard is used, we can't use credentials - browser security restriction
    # Use ["*"] explicitly for allow_origins (this allows ALL origins)
    use_credentials = False
    processed_origins = ["*"]
    print("CORS: Using wildcard '*' - allowing ALL origins, credentials disabled")
else:
    processed_origins = cors_origins if isinstance(cors_origins, list) else [cors_origins]
    print(f"CORS: Using specific origins: {processed_origins}")

print(f"CORS: allow_credentials={use_credentials}, allow_origins={processed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=processed_origins,
    allow_credentials=use_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
from app.middleware.rate_limit import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)


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
app.include_router(settings_api.router, prefix="/api/settings", tags=["settings"])

# Inject websocket manager into websocket router
websocket.set_websocket_manager(websocket_manager)

# Inject polling service into summary, machines, and status routers
summary.set_polling_service(polling_service)
machines.set_polling_service(polling_service)
status.set_polling_service(polling_service)


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize Redis (required) - raises RuntimeError on failure
    from app.utils.redis_client import init_redis
    init_redis()  # Raises RuntimeError if Redis is unavailable
    print("Redis client initialized")
    
    print("Starting background polling service...")
    await polling_service.start()
    print("Polling service started - monitoring all enabled machines")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    print(f"Shutting down {settings.APP_NAME}")
    print("Stopping background polling service...")
    await polling_service.stop()
    
    # Ensure all Telnet connections are closed (backup cleanup)
    try:
        from app.clients.telnet_client import close_all_connections
        await close_all_connections()
    except Exception as e:
        logger.warning(f"Error closing Telnet connections during shutdown: {e}")
    
    # Close Redis connection
    try:
        from app.utils.redis_client import close_redis
        await close_redis()
    except Exception as e:
        logger.warning(f"Error closing Redis connection during shutdown: {e}")
    
    print("Polling service stopped")
