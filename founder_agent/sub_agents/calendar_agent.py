import os, asyncio, json
from datetime import datetime
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

async def get_calendar_events(gmail_token: str = None) -> dict:
    """Fetches up to 10 upcoming events for today from Google Calendar."""
    if not gmail_token:
        return {'error': 'No Google token available'}
        
    try:
        creds_json = json.loads(gmail_token)
        creds = Credentials.from_authorized_user_info(creds_json)
        
        def _fetch_calendar():
            service = build('calendar', 'v3', credentials=creds)
            # Get the start and end of today
            now = datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
            
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

        return await asyncio.to_thread(_fetch_calendar)
    except Exception as e:
        return {'error': f"Calendar API error: {str(e)}"}

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
