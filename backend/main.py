import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
from api.routes import router as api_router
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.datastructures import MutableHeaders
import json
import os
from pydantic import BaseModel
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Stockast API",
    description="API for the Stockast trading bot and sentiment analysis.",
    version="0.1.0",
)

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
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
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