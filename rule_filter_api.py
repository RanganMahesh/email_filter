import os
import json
import sqlite3
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from rule_filter_client import match_rule


def authenticate_gmail_api(scopes):
    try:
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', scopes)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        return creds.token

    except Exception as e:
        print(f"Failed during authentication: {e}")
        return None


def apply_actions(access_token, email_id, actions):
    # NOTE: Implementing API based updates instead of using the client library directly
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        for action in actions:
            if action == 'mark_as_read':
                data = {'removeLabelIds': ['UNREAD']}
            elif action == 'move_to_inbox':
                data = {'addLabelIds': ['INBOX']}

            response = requests.post(f'https://www.googleapis.com/gmail/v1/users/me/messages/{email_id}/modify',
                                     headers=headers, json=data)
            response.raise_for_status()

    except Exception as e:
        print(f"Failed to execute action: {e}")


def apply_rules():
    with open('rules.json', 'r') as f:
        rules = json.load(f)

    service = authenticate_gmail_api(['https://www.googleapis.com/auth/gmail.modify'])
    conn = sqlite3.connect('emails.db')
    c = conn.cursor()
    for row in c.execute('SELECT * FROM emails'):
        for rule in rules:
            match_all = rule['conditions']['match'] == 'all'
            email_id, payload = row
            email = {
                'id': email_id,
                'payload': payload
            }
            match = match_rule(email, rule['conditions']['rules'], match_all)
            if match:
                apply_actions(service, email_id, rule['actions'])

    conn.close()


if __name__ == "__main__":
    apply_rules()
