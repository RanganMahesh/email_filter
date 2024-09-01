import unittest
from unittest.mock import patch, MagicMock
import sqlite3
import json
from gmail_client import fetch_emails, store_emails_in_sqlite
from rule_filter_client import apply_rules


class TestEmailFetchingAndStoring(unittest.TestCase):

    @patch('gmail_client.authenticate_gmail_api')
    def test_fetch_and_store_emails(self, mock_authenticate_gmail_api):
        mock_service = MagicMock()
        mock_authenticate_gmail_api.return_value = mock_service

        mock_service.users().messages().list.return_value.execute.return_value = {
            'messages': [{'id': 'test_email_id'}]
        }
        mock_service.users().messages().get.return_value.execute.return_value = {
            'id': 'test_email_id',
            'payload': {
                'headers': [{'name': 'Subject', 'value': 'Test Email'}]
            }
        }

        emails = fetch_emails()

        store_emails_in_sqlite(emails)

        conn = sqlite3.connect('emails.db')
        cur = conn.cursor()

        cur.execute('SELECT * FROM emails WHERE id=?', ('test_email_id',))
        result = cur.fetchone()

        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'test_email_id')

        payload = json.loads(result[1])
        self.assertEqual(payload['headers'][0]['value'], 'Test Email')

        conn.close()

class TestApplyingRulesAndCallingGmailAPI(unittest.TestCase):

    @patch('rule_filter_client.authenticate_gmail_api')
    @patch('rule_filter_client.apply_actions')
    @patch('rule_filter_client.open', new_callable=unittest.mock.mock_open, read_data=json.dumps([
        {
            "conditions": {
                "match": "all",
                "rules": [
                    {"field": "subject", "predicate": "contains", "value": "Test"}
                ]
            },
            "actions": ["mark_as_read"]
        }
    ]))
    def test_apply_rules(self, mock_open, mock_apply_actions, mock_authenticate_gmail_api):
        mock_service = MagicMock()
        mock_authenticate_gmail_api.return_value = mock_service

        conn = sqlite3.connect(':memory:')
        cur = conn.cursor()
        cur.execute('CREATE TABLE emails (id TEXT PRIMARY KEY, payload TEXT)')
        email_payload = {
            'headers': [{'name': 'Subject', 'value': 'Test Email'}]
        }
        cur.execute("INSERT INTO emails (id, payload) VALUES (?, ?)",
                    ('test_email_id', json.dumps(email_payload)))
        conn.commit()

        with patch('rule_filter_client.sqlite3.connect', return_value=conn):
            apply_rules()

        mock_apply_actions.assert_called_once_with(mock_service, 'test_email_id', ['mark_as_read'])

        conn.close()

if __name__ == '__main__':
    unittest.main()
