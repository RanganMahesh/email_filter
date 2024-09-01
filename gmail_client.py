import json
import os
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import sqlite3


def authenticate_gmail_api(scope):
    try:
        creds = None

        # NOTE: Tokens should not be stored without encryption directly, this is followed only for simplicity.
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', scope)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scope)
                creds = flow.run_local_server(port=0, prompt='consent')

            # Reuse the token in the next call
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

    except Exception as e:
        print(f"Failed during authentication: {e}")
        return None

    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        print(f"Failed to build Gmail API service: {e}")
        return None


def fetch_emails():
    email_data = []
    # NOTE: ReadOnly should suffice to fetch the emails
    gmail_service = authenticate_gmail_api(['https://www.googleapis.com/auth/gmail.readonly'])
    try:
        # NOTE: Emails fetched currently capped at 10, change maxResults accordingly
        results = gmail_service.users().messages().list(userId='me', maxResults=10, q='').execute()
        messages = results.get('messages', [])

        for message in messages:
            msg = gmail_service.users().messages().get(userId='me', id=message['id']).execute()
            email_data.append(msg)

    except Exception as e:
        print(f"Failed to fetch email: {e}")

    return email_data


def store_emails_in_sqlite(emails):
    try:
        conn = sqlite3.connect('emails.db')
        cur = conn.cursor()

        # EMAIL_ID is set as primary key, this should deduplicate entries in the DB
        cur.execute('CREATE TABLE IF NOT EXISTS emails (id TEXT PRIMARY KEY, payload TEXT)')
        for email in emails:

            # Dumping the entire payload so any property can be used in the rule set, can scope down based on requirement
            cur.execute("INSERT OR REPLACE INTO emails (id, payload) VALUES (?, ?)",
                        (email['id'], json.dumps(email.get('payload', {}))))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"An error occurred while updating the DB: {e}")


if __name__ == '__main__':
    mails = fetch_emails()
    store_emails_in_sqlite(mails)
