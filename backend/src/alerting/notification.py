import smtplib
import os
from twilio.rest import Client
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables for secure configuration
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))  # Default to 587 for TLS
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
RECIPIENT_PHONE_NUMBER = os.getenv('RECIPIENT_PHONE_NUMBER')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')

# Function to send email notification
def send_email(subject, body):
    """Send an email notification with the given subject and body."""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, RECIPIENT_EMAIL, msg.as_string())
        print(f"Email sent: {subject}")
    except Exception as e:
        print(f"Failed to send email: {e}")

# Function to send SMS notification
def send_sms(body):
    """Send an SMS notification with the given body."""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=body,
            from_=TWILIO_PHONE_NUMBER,
            to=RECIPIENT_PHONE_NUMBER
        )
        print(f"SMS sent: {message.sid}")
    except Exception as e:
        print(f"Failed to send SMS: {e}")

# Main function to send alerts via email and SMS
def send_alert(message):
    """
    Send an immediate alert via email and SMS.
    
    Args:
        message (str): Alert message from alert_generator.py, e.g., 
                       "MA Crossover signal for AAPL: BUY at 150.25"
    """
    subject = "Stock Trading Alert"
    send_email(subject, message)
    send_sms(message)

if __name__ == "__main__":
    # Test the notification system
    test_message = "Test signal for TEST: BUY at 100.00"
    send_alert(test_message)
