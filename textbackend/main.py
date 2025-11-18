import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from api.routes import router as api_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Stockast API",
    description="API for the Stockast trading bot and sentiment analysis.",
    version="0.1.0",
)

# CORS (Cross-Origin Resource Sharing) Middleware
# This allows your React Native frontend (running on a different port)
# to communicate with this backend.
# In a production environment, you should restrict origins for security.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include the API router from api/routes.py
# All routes defined in that file will be prefixed with /api
app.include_router(api_router, prefix="/api")

@app.get("/", tags=["Root"])
async def read_root():
    """A simple root endpoint to confirm the server is running."""
    return {"message": "Welcome to the Stockast API"}


if __name__ == "__main__":
    # This block allows you to run the server directly with `python main.py`
    # The frontend expects the server on port 3000.
    # The `reload=True` flag is great for development, as it restarts the server on code changes.
    logger.info("Starting Uvicorn server...")
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True, log_level="debug")