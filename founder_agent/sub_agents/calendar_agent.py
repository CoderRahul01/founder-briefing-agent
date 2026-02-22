import os
import json
from datetime import datetime
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

def get_calendar_events() -> dict:
    """Fetches up to 10 upcoming events for today from Google Calendar."""
    token_str = os.environ.get('GMAIL_OAUTH_TOKEN') # Using same env var for simplicity as it contains the multi-scope token
    if not token_str:
        return {'error': 'No Google token available'}
        
    creds_json = json.loads(token_str)
    creds = Credentials.from_authorized_user_info(creds_json)
    service = build('calendar', 'v3', credentials=creds)
    
    # Get the start and end of today
    now = datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    
    print(f"Fetching calendar events since {now}...")
    events_result = service.events().list(
        calendarId='primary', timeMin=now,
        maxResults=10, singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])
    
    event_list = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        event_list.append({
            'summary': event.get('summary', 'No Title'),
            'start': start,
            'description': event.get('description', '')
        })
        
    return {'events': event_list}

calendar_tool = FunctionTool(func=get_calendar_events)

calendar_agent = LlmAgent(
    name='calendar_agent',
    model='gemini-2.0-flash',
    description='Checks Google Calendar for today\'s meetings and schedules.',
    instruction='''
    You are an executive assistant. Use get_calendar_events to see what is on the founder's schedule today.
    Summarize the top 3 most important meetings or tasks.
    
    Focus on items that require preparation or external meetings. 
    Ignore generic blocks like "Deep Work" or "Lunch" unless they seem high priority.
    ''',
    tools=[calendar_tool],
)
