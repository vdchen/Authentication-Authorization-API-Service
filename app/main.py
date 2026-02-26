"""Main FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from aiocache import caches
from app.config import settings
from app.api.v1 import api_router
from app.db.session import init_db, close_db
from app.utils.redis_client import redis_client
import logging

# Setup Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles the startup and shutdown sequence safely.
    """
    # --- Startup ---
    logger.info("Starting %s...", settings.app_name)

    try:
        # Create Database Tables
        await init_db()
        logger.info("Database tables initialized.")

        # Connect to Redis (with health check)
        await redis_client.connect()
        logger.info("Connected to Redis.")

        # Configure aiocache to use Redis instead of memory
        caches.set_config({
            'default': {
                'cache': "aiocache.RedisCache",
                'endpoint': settings.redis_host,
                'port': settings.redis_port,
                'timeout': 1,
                'serializer': {
                    'class': "aiocache.serializers.JsonSerializer"
                }
            }
        })

    except Exception as e:
        logger.error("Startup failed: %s", e)
        raise

    logger.info("Startup complete. Application is ready.")

    yield

    # --- Shutdown ---
    logger.info("Shutting down...")

    # 1. Close Redis
    await redis_client.disconnect()

    # 2. Close Database Engine
    await close_db()

    logger.info("Cleanup finished. Goodbye!")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Authentication and authorization API service",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint for health check."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "healthy",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Simple health check endpoint for Docker/K8s."""
    return {"status": "healthy"}


if __name__ == "__main__":
    # Windows==asyncio/Linux==uvloop
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )