# DESCRIPTION: This file contains the service responsible for checking for new trading signals and notifying users.

import logging
import json
import datetime
from typing import Dict, Any

from sqlalchemy.orm import Session

# Assuming these are the correct import paths based on the project structure
from app.crud import crud_user, crud_watchlist
from app.services import signal_generator
from app.services.websocket_manager import ConnectionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define significant signal types for easier checking
SIGNIFICANT_SIGNALS = {'BULLISH', 'STRONG_BULLISH', 'BEARISH', 'STRONG_BEARISH'}

async def check_for_alerts(db: Session, websocket_manager: ConnectionManager) -> None:
    """
    Iterates through user watchlists, generates signals, and sends alerts via WebSocket.

    This function is intended to be run periodically as a background task.

    Args:
        db (Session): The database session.
        websocket_manager (ConnectionManager): The WebSocket connection manager.
    """
    logger.info("Starting alert check cycle...")
    try:
        users = crud_user.get_multi(db)
        if not users:
            logger.info("No active users found. Skipping alert check.")
            return

        for user in users:
            try:
                logger.info(f"Checking alerts for user_id: {user.id}")
                watchlist_items = crud_watchlist.get_multi_by_owner(db=db, owner_id=user.id)

                if not watchlist_items:
                    logger.info(f"User {user.id} has an empty watchlist. Skipping.")
                    continue

                for watchlist_item in watchlist_items:
                    symbol = watchlist_item.symbol
                    logger.debug(f"Processing symbol '{symbol}' for user {user.id}")

                    # Generate the latest signal for the stock
                    signal_data = await signal_generator.process_stock_for_signals(db=db, symbol=symbol)
                    
                    if not signal_data:
                        logger.warning(f"No signal data returned for symbol {symbol}")
                        continue

                    signal_type = signal_data.get("signal_type")
                    reason = signal_data.get("reason")

                    # Check if the signal is significant enough to warrant an alert
                    if signal_type in SIGNIFICANT_SIGNALS:
                        # Get the current UTC timestamp
                        timestamp = datetime.datetime.now(datetime.timezone.utc).timestamp()
                        
                        alert_message: Dict[str, Any] = {
                            "symbol": symbol,
                            "signal_type": signal_type,
                            "reason": reason,
                            "timestamp": timestamp,
                        }
                        
                        json_message = json.dumps(alert_message)
                        
                        # Send the alert to the specific user's WebSocket connection
                        await websocket_manager.send_personal_message(json_message, user.id)
                        
                        logger.info(f"Sent alert to user {user.id} for {symbol}: {signal_type} - {reason}")
                    else:
                        # Log neutral signals for debugging/monitoring purposes
                        logger.info(f"No significant alert generated for {symbol} for user {user.id} (Signal: {signal_type})")

            except Exception as e:
                logger.error(f"Error processing alerts for user {user.id}: {e}", exc_info=True)
                # Continue to the next user even if one fails
                continue

    except Exception as e:
        logger.error(f"A top-level error occurred during the alert check cycle: {e}", exc_info=True)
    finally:
        logger.info("Alert check cycle finished.")
