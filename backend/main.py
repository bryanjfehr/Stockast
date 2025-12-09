import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
from api.routes import router as api_router
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware
import json
import os
from pydantic import BaseModel
from typing import Optional
import numpy as np
import torch
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from ml.data_fetcher import fetch_exchange_info, fetch_multi_histories
from ml.data_sampler import generate_samples
from ml.train import train_hrm
from db.utils import get_db
from db.models import Symbol, Base
from db.utils import engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Stockast API",
    description="API for the Stockast trading bot and sentiment analysis.",
    version="0.1.0",
)

scheduler = BackgroundScheduler()

# Create database tables
Base.metadata.create_all(bind=engine)

# --- API Key Persistence ---
CONFIG_FILE = "config.json"

class ApiKeys(BaseModel):
    exchange_api_key: str
    exchange_api_secret: str
    santiment_api_key: str

def load_api_keys() -> Optional[ApiKeys]:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return ApiKeys(**json.load(f))
    return None

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

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        logger.info(f"Request: {request.method} {request.url.path}")

        response = await call_next(request)

        process_time = (time.time() - start_time) * 1000
        
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
        
        logger.info(f"Response: {response.status_code} ({process_time:.2f}ms) Body: {response_body.decode('utf-8')}")
        
        return Response(content=response_body, status_code=response.status_code, headers=dict(response.headers), media_type=response.media_type)

app.add_middleware(LoggingMiddleware)

# --- Startup Checks ---
def startup_checks(db: Session):
    """
    Run on app start: Check for API keys and the pre-trained model.
    """
    # Step 1: Check for API keys
    if not os.path.exists(CONFIG_FILE):
        logging.warning("API keys not found in config.json. Some features may be disabled until keys are provided via the API.")
    else:
        logging.info("API keys file found.")

    # Step 2: Check for the pre-trained model
    model_path = 'hrm_intra.pth'
    if not os.path.exists(model_path):
        logging.critical(f"CRITICAL: Pre-trained model '{model_path}' not found.")
        logging.critical("The application cannot make predictions without the model.")
        logging.critical("Please run the training script to generate the model: python scripts/build_and_train.py")
        # In a production environment, you might want to exit here:
        # sys.exit(1)
    else:
        logging.info(f"Pre-trained model '{model_path}' found.")

    # Trade logic ready after checks
    logging.info("Startup checks complete.")

@app.on_event("startup")
def startup_event():
    db = next(get_db())
    startup_checks(db)
    scheduler.add_job(lambda: fetch_exchange_info(refresh=True), 'interval', hours=24)  # Daily refresh
    scheduler.start()

# Include the API router from api/routes.py
# All routes defined in that file will be prefixed with /api
app.include_router(api_router, prefix="/api")

# --- Symbol Data ---
# In a real app, this would be in a separate file, e.g., api/market_data.py
# and would use a proper client for the exchange.
async def get_all_symbols_placeholder():
    """
    Placeholder for fetching all symbols from MEXC.
    This should be replaced with a real API call.
    """
    # This is a placeholder. In a real implementation, you would make an API call
    # to MEXC's /api/v3/exchangeInfo endpoint and parse the symbols.
    return ["BTC/USDT", "ETH/USDT", "XRP/USDT", "SOL/USDT", "DOGE/USDT"]

@app.get("/api/exchange/symbols", tags=["Market Data"])
async def get_exchange_symbols():
    """Returns a list of all available trading symbols from the exchange."""
    symbols = await get_all_symbols_placeholder()
    return symbols

@app.post("/api/keys", status_code=200)
async def save_api_keys(keys: ApiKeys):
    """Saves API keys to a config file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(keys.dict(), f, indent=4)
        return {"message": "API keys saved successfully."}
    except Exception as e:
        logger.error(f"Failed to save API keys: {e}")
        raise HTTPException(status_code=500, detail="Failed to save API keys.")

@app.get("/api/keys/status")
async def get_keys_status():
    """Checks if the API keys are configured."""
    keys = load_api_keys()
    return {"hasKeys": keys is not None}

# At startup, try to load keys.
# In a real app, you'd pass this to your services that need them.
api_keys = load_api_keys()

@app.get("/", tags=["Root"])
async def read_root():
    """A simple root endpoint to confirm the server is running."""
    return {"message": "Welcome to the Stockast API"}


if __name__ == "__main__":
    # This block allows you to run the server directly with `python main.py`
    # The frontend expects the server on port 3000.
    # The `reload=True` flag is great for development, as it restarts the server on code changes.
    if api_keys:
        logger.info("API keys loaded from config.json.")
    else:
        logger.warning("API keys not found. Waiting for frontend to provide them.")
    logger.info("Starting Uvicorn server...")
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True, log_level="debug")