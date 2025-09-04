import asyncio
import json
import logging
import datetime

from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.security import get_current_user
from app.crud import crud_watchlist
from app.db.session import get_db
from app.models.user import User
from app.services import data_fetcher
from app.services.websocket_manager import manager
from app.tasks import scheduler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS middleware
# In a production environment, you should restrict this to your frontend's domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS if settings.BACKEND_CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the main API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
async def startup_event():
    """Actions to perform on application startup."""
    logger.info("Starting background task scheduler...")
    scheduler.start_scheduler()
    logger.info("Background task scheduler started.")


@app.on_event("shutdown")
async def shutdown_event():
    """Actions to perform on application shutdown."""
    logger.info("Shutting down background task scheduler...")
    scheduler.shutdown_scheduler()
    logger.info("Background task scheduler shut down.")


@app.get("/")
def read_root():
    """Root endpoint for health checks."""
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}


@app.websocket("/ws/alerts")
async def websocket_alerts_endpoint(
    websocket: WebSocket, current_user: User = Depends(get_current_user)
):
    """Handles WebSocket connections for sending trading signal alerts to authenticated users."""
    logger.info(f"WebSocket alert connection opened for user: {current_user.id}")
    await manager.connect(websocket, current_user.id)
    try:
        while True:
            # Keep the connection alive and listen for client disconnects.
            data = await websocket.receive_text()
            logger.debug(f"Received unexpected message on alerts websocket from user {current_user.id}: {data}")
    except WebSocketDisconnect:
        logger.info(f"WebSocket alert connection closed for user: {current_user.id}")
        manager.disconnect(current_user.id)
    except Exception as e:
        logger.error(f"Error in WebSocket alert connection for user {current_user.id}: {e}")
        manager.disconnect(current_user.id)


@app.websocket("/ws/stocks/realtime")
async def websocket_realtime_endpoint(
    websocket: WebSocket, current_user: User = Depends(get_current_user)
):
    """Streams real-time stock data for the user's watchlist."""
    logger.info(f"Real-time WebSocket connection opened for user: {current_user.id}")
    # Although this is a streaming endpoint, we register with the manager
    # in case other services need to push messages (e.g., notifications).
    await manager.connect(websocket, current_user.id)
    try:
        while True:
            db: Session = next(get_db())
            try:
                watchlist_items = crud_watchlist.get_multi_by_owner(
                    db=db, owner_id=current_user.id
                )
                if not watchlist_items:
                    logger.debug(f"User {current_user.id} has an empty watchlist. Waiting...")
                else:
                    for item in watchlist_items:
                        symbol = item.symbol
                        try:
                            quote_data = await data_fetcher.fetch_realtime_quote(symbol)
                            if quote_data and quote_data.get("price") is not None:
                                message = {
                                    "symbol": symbol,
                                    "price": quote_data["price"],
                                    "timestamp": datetime.datetime.now(
                                        datetime.timezone.utc
                                    ).isoformat(),
                                }
                                await websocket.send_text(json.dumps(message))
                            else:
                                logger.warning(
                                    f"Could not fetch real-time data for symbol: {symbol}"
                                )
                        except Exception as fetch_error:
                            logger.error(
                                f"Error fetching data for {symbol} for user {current_user.id}: {fetch_error}"
                            )
            finally:
                db.close()

            await asyncio.sleep(settings.REALTIME_DATA_FETCH_INTERVAL_SECONDS)

    except WebSocketDisconnect:
        # This might not be hit if we only send, but included for completeness.
        logger.info(f"Real-time WebSocket connection closed for user: {current_user.id}")
        manager.disconnect(current_user.id)
    except Exception as e:
        # This will catch errors from send_text if the client disconnects abruptly.
        logger.error(f"Error in real-time WebSocket for user {current_user.id}: {e}")
        manager.disconnect(current_user.id)
