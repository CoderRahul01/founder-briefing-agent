import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

def send_whatsapp_message(to_number: str, text: str):
    """
    Sends a WhatsApp message via Twilio Sandbox.
    Handles message chunking because WhatsApp has a ~1600 char limit.
    """
    if not to_number:
        return

    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_number = os.getenv('TWILIO_PHONE_NUMBER', 'whatsapp:+14155238886')

    if not account_sid or not auth_token:
        print("Twilio credentials missing. Skipping WhatsApp delivery.")
        return

    try:
        client = Client(account_sid, auth_token)
    except Exception as e:
        print(f"Failed to initialize Twilio client. Skipping WhatsApp delivery. Error: {e}")
        return

    # WhatsApp officially supports 1600 chars. We chunk around 1500 to be safe.
    max_length = 1500
    chunks = []
    
    # Split by double newline to try preserving paragraph structure
    paragraphs = text.split('\n\n')
    current_chunk = ""

    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 2 < max_length:
            if current_chunk:
                current_chunk += "\n\n"
            current_chunk += paragraph
        else:
            if current_chunk:
                chunks.append(current_chunk)
            
            # If a single paragraph is larger than max_length, force split it
            while len(paragraph) > max_length:
                chunks.append(paragraph[:max_length])
                paragraph = paragraph[max_length:]
            current_chunk = paragraph

    if current_chunk:
        chunks.append(current_chunk)

    print(f"Sending WhatsApp message in {len(chunks)} chunks to {to_number}...")
    
    # Ensure to_number is formatted correctly with 'whatsapp:' prefix
    if not to_number.startswith('whatsapp:'):
        to_number = f"whatsapp:{to_number}"

    for i, chunk in enumerate(chunks, 1):
        try:
            message = client.messages.create(
                from_=from_number,
                body=chunk,
                to=to_number
            )
            print(f"WhatsApp chunk {i}/{len(chunks)} sent successfully. SID: {message.sid}")
        except Exception as e:
            print(f"Failed to send WhatsApp chunk {i}: {e}")

