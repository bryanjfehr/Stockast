import scrapy
from scrapy.crawler import CrawlerProcess
import schedule
import time
import logging
import os
from transformers import pipeline
from database.db_operations import store_article_data

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# List of financial sites to scrape (focused on TSX stock predictions)
SITES_TO_SCRAPE = [
    'https://seekingalpha.com/market-news',
    'https://www.fool.ca/category/tsx/',
    # Add more TSX-focused sites after research
]

# Initialize NLP models
sentiment_analyzer = pipeline('sentiment-analysis', model='distilbert-base-uncased-finetuned-sst-2-english')
ner_model = pipeline('ner', model='dbmdz/bert-large-cased-finetuned-conll03-english')

class ArticleSpider(scrapy.Spider):
    name = 'article_spider'

    def start_requests(self):
        for url in SITES_TO_SCRAPE:
            try:
                yield scrapy.Request(url=url, callback=self.parse)
            except Exception as e:
                logging.error(f"Failed to request {url}: {str(e)}")

    def parse(self, response):
        try:
            articles = response.css('article')
            if not articles:
                logging.warning(f"No articles found on {response.url}")
                return

            for article in articles:
                title = article.css('h2::text').get(default='').strip()
                content = article.css('p::text').get(default='').strip()
                date = article.css('time::text').get(default='').strip()
                url = article.css('a::attr(href)').get(default='')

                if title and content:
                    # Extract stock symbols (TSX stocks end with '.TO')
                    entities = ner_model(content)
                    stock_symbols = [entity['word'] for entity in entities if entity['entity'] == 'ORG' and entity['word'].endswith('.TO')]

                    if not stock_symbols:
                        continue  # Skip if no TSX stocks are mentioned

                    # Analyze sentiment
                    sentiment = sentiment_analyzer(content[:512])[0]  # Limit to 512 tokens for efficiency

                    # Extract timeline (basic keyword approach)
                    content_lower = content.lower()
                    timeline = ('short-term' if 'short term' in content_lower else 
                              'mid-term' if 'mid term' in content_lower else 
                              'long-term')

                    # Store data
                    for symbol in stock_symbols:
                        article_data = {
                            'site': response.url,
                            'date': date,
                            'symbol': symbol,
                            'title': title,
                            'content': content,
                            'sentiment': sentiment['label'],
                            'confidence': sentiment['score'],
                            'timeline': timeline,
                            'url': url
                        }
                        try:
                            store_article_data(article_data)
                            logging.info(f"Stored article: {title} for {symbol}")
                        except Exception as e:
                            logging.error(f"Failed to store article {title}: {str(e)}")
        except Exception as e:
            logging.error(f"Error parsing {response.url}: {str(e)}")

def run_scraper():
    try:
        process = CrawlerProcess({
            'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'DOWNLOAD_DELAY': 2,  # Prevent overloading servers
            'LOG_LEVEL': 'INFO',
        })
        process.crawl(ArticleSpider)
        process.start()
    except Exception as e:
        logging.error(f"Scraper failed: {str(e)}")

# Schedule to run daily at 5 AM
schedule.every().day.at("05:00").do(run_scraper)

logging.info("Web scraper scheduled to run daily at 5 AM.")

# Keep script running for scheduled tasks
while True:
    try:
        schedule.run_pending()
        time.sleep(60)
    except Exception as e:
        logging.error(f"Scheduling error: {str(e)}")
