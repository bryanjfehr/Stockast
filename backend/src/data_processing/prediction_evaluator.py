import pandas as pd
import logging
from datetime import datetime, timedelta
from database.db_operations import get_predictions, get_stock_prices, update_accuracy_score
from apscheduler.schedulers.blocking import BlockingScheduler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Utility function to calculate price movement category
def calculate_price_movement(price_change):
    """
    Categorize price movement based on percentage change.
    - Positive: > 1%
    - Negative: < -1%
    - Neutral: between -1% and 1%
    """
    if price_change > 0.01:
        return 'positive'
    elif price_change < -0.01:
        return 'negative'
    else:
        return 'neutral'

# Utility function to compare predicted sentiment with actual movement
def compare_sentiment(predicted, actual):
    """
    Check if the predicted sentiment matches the actual price movement.
    """
    return predicted == actual

# Main function to evaluate predictions for a given source and time frame
def evaluate_predictions(source, time_frame, start_date, end_date):
    """
    Evaluate the accuracy of predictions for a specific source and time frame.
    """
    # Define evaluation period based on time frame
    if time_frame == 'short-term':
        evaluation_days = 5
    elif time_frame == 'mid-term':
        evaluation_days = 30
    else:  # long-term
        evaluation_days = 90

    # Retrieve predictions from the database
    predictions = get_predictions(source, start_date, end_date)
    if predictions.empty:
        logging.warning(f"No predictions found for {source} between {start_date} and {end_date}.")
        return None

    accuracies = []
    for _, prediction in predictions.iterrows():
        stock = prediction['symbol']
        prediction_date = prediction['date']
        sentiment = prediction['sentiment']

        # Retrieve stock prices for the evaluation period
        end_eval_date = prediction_date + timedelta(days=evaluation_days)
        prices = get_stock_prices(stock, prediction_date, end_eval_date)

        if prices.empty or len(prices) < 2:
            continue  # Skip if insufficient price data

        # Calculate percentage price change
        initial_price = prices.iloc[0]['close']
        final_price = prices.iloc[-1]['close']
        price_change = (final_price - initial_price) / initial_price

        # Determine actual price movement category
        actual_movement = calculate_price_movement(price_change)

        # Compare with predicted sentiment
        is_accurate = compare_sentiment(sentiment, actual_movement)
        accuracies.append(is_accurate)

    if accuracies:
        accuracy = sum(accuracies) / len(accuracies)
        return accuracy
    else:
        return None

# Main function to evaluate all sources and time frames
def main():
    """
    Evaluate predictions for all sources and time frames, and update accuracy scores in the database.
    """
    sources = ['source1', 'source2']  # Replace with actual sources
    time_frames = ['short-term', 'mid-term', 'long-term']
    evaluation_period = 30  # days for historical evaluation

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=evaluation_period)

    for source in sources:
        for time_frame in time_frames:
            accuracy = evaluate_predictions(source, time_frame, start_date, end_date)
            if accuracy is not None:
                try:
                    update_accuracy_score(source, time_frame, accuracy)
                    logging.info(f"Updated accuracy for {source} ({time_frame}): {accuracy:.2%}")
                except Exception as e:
                    logging.error(f"Failed to update accuracy for {source} ({time_frame}): {str(e)}")

# Schedule the evaluation to run periodically (e.g., weekly)
if __name__ == '__main__':
    scheduler = BlockingScheduler()
    scheduler.add_job(main, 'interval', weeks=1)  # Adjust interval as needed
    logging.info("Prediction evaluator scheduled to run weekly.")
    scheduler.start()
