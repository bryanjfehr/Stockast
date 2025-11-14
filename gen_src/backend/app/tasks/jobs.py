import logging
from sqlalchemy.orm import Session

# Assuming these are the correct import paths based on the project structure
from app.db.session import get_db
from app.services import data_fetcher, alert_service
from app.services.websocket_manager import WebsocketManager
from app.crud import crud_stock
from app.schemas.stock import StockDataCreate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def update_stock_data_job():
    """
    Asynchronous job to fetch the latest active stock data and update the database.
    """
    logger.info("Starting stock data update job...")
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        active_stocks = await data_fetcher.fetch_tsx_active_stocks()
        if not active_stocks:
            logger.info("No active stocks fetched. Job finished.")
            return

        for stock_data_dict in active_stocks:
            try:
                # Pydantic model will only use fields defined in StockDataCreate
                stock_data_create_instance = StockDataCreate(**stock_data_dict)
                # Assuming crud_stock.create_or_update_stock_data is an async function
                await crud_stock.create_or_update_stock_data(
                    db=db, stock_data_in=stock_data_create_instance
                )
            except Exception as e:
                logger.error(
                    f"Error processing stock data: {stock_data_dict}. Error: {e}"
                )

        logger.info(
            f"Stock data update job finished. Processed {len(active_stocks)} stocks."
        )

    except Exception as e:
        logger.error(
            f"An error occurred during the stock data update job: {e}", exc_info=True
        )
    finally:
        db.close()
        logger.info("Database session closed for stock data update job.")


async def check_alerts_job(websocket_manager: WebsocketManager):
    """
    Asynchronous job to check for new trading signals and send alerts to connected users.

    Args:
        websocket_manager (WebsocketManager): The manager for handling websocket connections.
    """
    logger.info("Starting alert checking job...")
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        # Assuming alert_service.check_for_alerts is an async function
        await alert_service.check_for_alerts(db=db, websocket_manager=websocket_manager)
        logger.info("Alerts checked successfully.")
    except Exception as e:
        logger.error(
            f"An error occurred during the alert checking job: {e}", exc_info=True
        )
    finally:
        db.close()
        logger.info("Database session closed for alert checking job.")
