import re
import nltk
from transformers import pipeline

# Load FinBERT model for financial sentiment analysis
sentiment_analyzer = pipeline('sentiment-analysis', model='ProsusAI/finbert')

def get_sentiment_scores(article_content, stock_symbols):
    """
    Analyzes sentiment for each stock symbol in the article content.
    
    Args:
        article_content (str): The full text of the article.
        stock_symbols (list): List of stock symbols (e.g., ['ABC.TO', 'XYZ.TO']) mentioned in the article.
    
    Returns:
        dict: A dictionary with stock symbols as keys and their corresponding sentiment scores as values.
              Scores range from -1 (negative) to 1 (positive), with 0 as neutral.
    """
    # Ensure article_content is a string and not empty
    if not isinstance(article_content, str) or not article_content.strip():
        return {symbol: 0 for symbol in stock_symbols}
    
    # Split article into sentences
    sentences = nltk.sent_tokenize(article_content)
    
    sentiment_results = {}
    
    for symbol in stock_symbols:
        # Find sentences mentioning the symbol using regex with word boundaries
        relevant_sentences = [sent for sent in sentences if re.search(r'\b' + re.escape(symbol) + r'\b', sent)]
        
        if not relevant_sentences:
            sentiment_results[symbol] = 0  # Neutral if no relevant sentences
            continue
        
        # Analyze sentiment for each relevant sentence
        sentiments = []
        for sent in relevant_sentences:
            result = sentiment_analyzer(sent)[0]
            label = result['label']
            score = result['score']
            # Map label to numerical score: positive (1), negative (-1), neutral (0)
            if label == 'positive':
                sentiments.append(1 * score)
            elif label == 'negative':
                sentiments.append(-1 * score)
            else:
                sentiments.append(0)
        
        # Aggregate sentiments by averaging
        avg_sentiment = sum(sentiments) / len(sentiments)
        sentiment_results[symbol] = round(avg_sentiment, 4)  # Round for readability
    
    return sentiment_results

# Example usage for testing
if __name__ == "__main__":
    # Sample article content
    sample_content = """
    The stock ABC.TO is expected to rise due to strong earnings this quarter.
    However, XYZ.TO might face challenges in the short term due to market volatility.
    """
    sample_symbols = ['ABC.TO', 'XYZ.TO']
    
    # Analyze sentiment
    results = get_sentiment_scores(sample_content, sample_symbols)
    
    # Print results
    for symbol, sentiment in results.items():
        print(f"{symbol}: Sentiment Score = {sentiment}")
