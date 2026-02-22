import os
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

def get_urgent_emails() -> dict:
    """Fetches top 10 unread emails from Gmail and returns subjects + senders."""
    # Load OAuth token from environment (passed from MongoDB by deliver_brief)
    token_str = os.environ.get('GMAIL_OAUTH_TOKEN')
    if not token_str:
        return {'error': 'No Gmail token available'}
        
    import json
    creds_json = json.loads(token_str)
    creds = Credentials.from_authorized_user_info(creds_json)
    service = build('gmail', 'v1', credentials=creds)
    results = service.users().messages().list(
        userId='me', q='is:unread', maxResults=10
    ).execute()
    messages = results.get('messages', [])
    email_data = []
    for msg in messages[:5]:
        detail = service.users().messages().get(userId='me', id=msg['id']).execute()
        headers = {h['name']: h['value'] for h in detail['payload']['headers']}
        email_data.append({'from': headers.get('From',''), 'subject': headers.get('Subject','')})
    return {'unread_count': len(messages), 'top_emails': email_data}

inbox_tool = FunctionTool(func=get_urgent_emails)

inbox_agent = LlmAgent(
    name='inbox_agent',
    model='gemini-2.0-flash',
    description='Reads Gmail and surfaces the most urgent emails for founder review.',
    instruction='''
    You are an executive assistant. Use get_urgent_emails to pull inbox data.
    List the top 3 emails that need the founder's attention today.
    For each: one line with sender + subject + why it is urgent.

    Skip newsletters, notifications, and anything obviously low priority.
    ''',
    tools=[inbox_tool],
)
