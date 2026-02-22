import base64
import os
from email.message import EmailMessage
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

def send_email():
    try:
        token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'secrets', 'token.json')
        creds = Credentials.from_authorized_user_file(token_path)
        service = build('gmail', 'v1', credentials=creds)

        message = EmailMessage()
        message.set_content('This is a test email from your Founder Briefing Agent.')
        message['To'] = 'rahulpandey.creates@gmail.com'
        message['Subject'] = 'Test Email'

        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {
            'raw': encoded_message
        }
        send_message = (service.users().messages().send(userId="me", body=create_message).execute())
        print(f'Message Id: {send_message["id"]}')
    except Exception as error:
        print(f'An error occurred: {error}')

if __name__ == '__main__':
    send_email()
