import json
import sqlite3
from datetime import datetime
from dateutil import parser
from gmail_client import authenticate_gmail_api


def parse_headers(payload):
    # Extract the headers and store them in a dictionary for easy of use
    headers = {}
    for header in payload.get('headers', []):
        name = header['name'].lower()
        headers[name] = header['value']
    return headers


def match_rule(email, conditions, match_all):
    headers = parse_headers(json.loads(email['payload']))
    matches = []

    for condition in conditions:
        field, predicate, value = condition['field'], condition['predicate'], condition['value']
        field_value = headers.get(field, '')

        # Handle DateTime based filters, currently supports only dates
        if field == 'received_at':
            email_date = parser.parse(headers.get('date', '0')).replace(tzinfo=None)
            days_diff = (datetime.utcnow() - email_date).days

            if predicate == 'is_less_than':
                matches.append(days_diff < value)
            elif predicate == 'is_greater_than':
                matches.append(days_diff > value)

        else:
            if predicate == 'contains':
                matches.append(value in field_value)
            elif predicate == 'not_contains':
                matches.append(value not in field_value)
            elif predicate == 'equals':
                matches.append(value == field_value)
            elif predicate == 'not_equals':
                matches.append(value != field_value)

    return all(matches) if match_all else any(matches)


def apply_actions(service, email_id, actions):
    try:
        # Supports mark as read / move to inbox, can be extended for more requirements
        for action in actions:
            body = {}
            if action == 'mark_as_read':
                body = {'removeLabelIds': ['UNREAD']}
            elif action == 'move_to_inbox':
                # NOTE: Currently moves to inbox, can be converted to a variable/ENUM if more options are required
                body = {'addLabelIds': ['INBOX']}

            service.users().messages().modify(
                userId='me',
                id=email_id,
                body=body
            ).execute()

    except Exception as e:
        print(f"Failed to execute action: {e}")


def apply_rules():
    with open('rules.json', 'r') as f:
        rules = json.load(f)

    # Reuse authentication from other script with a different scope to allow updates
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
