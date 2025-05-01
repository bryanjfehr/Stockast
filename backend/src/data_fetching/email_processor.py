import imaplib
import email
import schedule
import time
import re
import logging
import os
from database.db_operations import add_to_watchlist

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Email credentials (loaded from environment variables for security)
EMAIL_ACCOUNT = os.getenv('EMAIL_ACCOUNT')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

if not EMAIL_ACCOUNT or not EMAIL_PASSWORD:
    logging.error("Email credentials not found. Please set EMAIL_ACCOUNT and EMAIL_PASSWORD environment variables.")
    exit(1)

def process_emails():
    try:
        # Connect to the IMAP server (Gmail in this case)
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        mail.select('inbox')

        # Search for unread emails from Google Alerts
        status, messages = mail.search(None, '(UNSEEN FROM "googlealerts-noreply@google.com")')
        if status != 'OK':
            logging.error("Failed to search for emails.")
            return

        mail_ids = messages[0].split()
        logging.info(f"Found {len(mail_ids)} unread Google Alert emails.")

        for mail_id in mail_ids:
            status, msg_data = mail.fetch(mail_id, '(RFC822)')
            if status != 'OK':
                logging.error(f"Failed to fetch email ID {mail_id}.")
                continue

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    # Extract email body
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == 'text/plain':
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()

                    # Find stock symbols in the email body (e.g., "ABC.TO")
                    stock_symbols = re.findall(r'\b[A-Z]{1,4}\.TO\b', body)
                    for symbol in stock_symbols:
                        logging.info(f"Adding {symbol} to watchlist.")
                        add_to_watchlist(symbol)

            # Mark the email as read
            mail.store(mail_id, '+FLAGS', '\Seen')

        mail.close()
        mail.logout()
    except Exception as e:
        logging.error(f"Error processing emails: {e}")

# Schedule the task to run at 4 AM and 4 PM daily
schedule.every().day.at("04:00").do(process_emails)
schedule.every().day.at("16:00").do(process_emails)

logging.info("Email processor scheduled to run at 4 AM and 4 PM daily.")

# Keep the script running to check for scheduled tasks
while True:
    schedule.run_pending()
    time.sleep(60)
