import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']

# Use paths relative to the script location
import pathlib
script_dir = pathlib.Path(__file__).parent.resolve()
project_root = script_dir.parent
TOKEN_PATH = project_root / 'secrets' / 'token.json'
CREDENTIALS_PATH = project_root / 'secrets' / 'credentials.json'

def main():
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing token...")
            creds.refresh(Request())
        else:
            print("Requesting new token...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    print("Scopes successfully added.")

if __name__ == '__main__':
    main()
