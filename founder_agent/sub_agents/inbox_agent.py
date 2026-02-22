import os, asyncio, json
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

async def get_urgent_emails(gmail_token: str = None) -> dict:
    """Fetches top 10 unread emails from Gmail and returns subjects + senders."""
    if not gmail_token:
        return {'error': 'No Gmail token available'}
        
    try:
        creds_json = json.loads(gmail_token)
        creds = Credentials.from_authorized_user_info(creds_json)
        
        # We run the blocking Gmail API calls in a separate thread to avoid blocking the event loop
        def _fetch_emails():
            service = build('gmail', 'v1', credentials=creds)
            results = service.users().messages().list(
                userId='me', q='is:unread', maxResults=10
            ).execute()
            messages = results.get('messages', [])
            email_data = []
            for msg in messages[:5]:
                detail = service.users().messages().get(userId='me', id=msg['id']).execute()
                headers = {h['name']: h['value'] for h in detail['payload']['headers']}
                email_data.append({
                    'from': headers.get('From',''), 
                    'subject': headers.get('Subject','')
                })
            return {'unread_count': len(messages), 'top_emails': email_data}

        return await asyncio.to_thread(_fetch_emails)
    except Exception as e:
        return {'error': f"Gmail API error: {str(e)}"}

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
