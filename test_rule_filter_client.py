import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, mock_open, call

from rule_filter_client import parse_headers, match_rule, apply_actions, apply_rules


class TestParseHeaders(unittest.TestCase):

    def test_parse_headers(self):
        payload = {
            'headers': [
                {'name': 'From', 'value': 'example@example.com'},
                {'name': 'Subject', 'value': 'Test Email'}
            ]
        }
        expected = {
            'from': 'example@example.com',
            'subject': 'Test Email'
        }
        result = parse_headers(payload)
        self.assertEqual(result, expected)


class TestMatchRule(unittest.TestCase):

    @patch('rule_filter_client.parser.parse')
    def test_received_at_greater_than(self, mock_parse):
        mock_parse.return_value = datetime.now() - timedelta(days=10)

        email = {
            'payload': '{"headers": [{"name": "Date", "value": "Sat, 31 Aug 2024 15:44:49 +0000"}]}'
        }
        conditions = [{'field': 'received_at', 'predicate': 'is_greater_than', 'value': 5}]
        match_all = True

        result = match_rule(email, conditions, match_all)
        self.assertTrue(result)

    @patch('rule_filter_client.parser.parse')
    def test_received_at_less_than(self, mock_parse):
        mock_parse.return_value = datetime.now() - timedelta(days=1)

        email = {
            'payload': '{"headers": [{"name": "Date", "value": "Sat, 31 Aug 2024 15:44:49 +0000"}]}'
        }
        conditions = [{'field': 'received_at', 'predicate': 'is_less_than', 'value': 5}]
        match_all = True

        result = match_rule(email, conditions, match_all)
        self.assertTrue(result)

    @patch('rule_filter_client.parser.parse')
    def test_contains_field(self, mock_parse):
        email = {
            'payload': '{"headers": [{"name": "Subject", "value": "Test Email"}]}'
        }
        conditions = [{'field': 'subject', 'predicate': 'contains', 'value': 'Test'}]
        match_all = True

        result = match_rule(email, conditions, match_all)
        self.assertTrue(result)

    @patch('rule_filter_client.parser.parse')
    def test_not_contains_field(self, mock_parse):
        email = {
            'payload': '{"headers": [{"name": "Subject", "value": "Test Email"}]}'
        }
        conditions = [{'field': 'subject', 'predicate': 'not_contains', 'value': 'Spam'}]
        match_all = True

        result = match_rule(email, conditions, match_all)
        self.assertTrue(result)

    @patch('rule_filter_client.parser.parse')
    def test_equals_field(self, mock_parse):
        email = {
            'payload': '{"headers": [{"name": "Subject", "value": "Test Email"}]}'
        }
        conditions = [{'field': 'subject', 'predicate': 'equals', 'value': 'Test Email'}]
        match_all = True

        result = match_rule(email, conditions, match_all)
        self.assertTrue(result)

    @patch('rule_filter_client.parser.parse')
    def test_not_equals_field(self, mock_parse):
        email = {
            'payload': '{"headers": [{"name": "Subject", "value": "Test Email"}]}'
        }
        conditions = [{'field': 'subject', 'predicate': 'not_equals', 'value': 'Spam'}]
        match_all = True

        result = match_rule(email, conditions, match_all)
        self.assertTrue(result)

    @patch('rule_filter_client.parser.parse')
    def test_all_rules_matches(self, mock_parse):
        email = {
            'payload': '{"headers": [{"name": "Subject", "value": "Test Email"}]}'
        }
        conditions = [
            {'field': 'subject', 'predicate': 'contains', 'value': 'Test'},
            {'field': 'subject', 'predicate': 'equals', 'value': 'Test Email'}
        ]
        match_all = True

        result = match_rule(email, conditions, match_all)
        self.assertTrue(result)

    @patch('rule_filter_client.parser.parse')
    def test_any_rule_match(self, mock_parse):
        email = {
            'payload': '{"headers": [{"name": "Subject", "value": "Test Email"}]}'
        }
        conditions = [
            {'field': 'subject', 'predicate': 'contains', 'value': 'Spam'},
            {'field': 'subject', 'predicate': 'equals', 'value': 'Test Email'}
        ]
        match_all = False

        result = match_rule(email, conditions, match_all)
        self.assertTrue(result)


class TestApplyActions(unittest.TestCase):

    def test_mark_as_read(self):
        mock_service = MagicMock()

        apply_actions(mock_service, 'test_email_id', ['mark_as_read'])

        mock_service.users().messages().modify.assert_called_once_with(
            userId='me',
            id='test_email_id',
            body={'removeLabelIds': ['UNREAD']}
        )

    def test_move_to_inbox(self):
        mock_service = MagicMock()

        apply_actions(mock_service, 'test_email_id', ['move_to_inbox'])

        mock_service.users().messages().modify.assert_called_once_with(
            userId='me',
            id='test_email_id',
            body={'addLabelIds': ['INBOX']}
        )

    @patch('builtins.print')
    def test_exception_message(self, mock_print):
        mock_service = MagicMock()

        mock_service.users().messages().modify.side_effect = Exception("API Error")

        apply_actions(mock_service, 'test_email_id', ['mark_as_read'])

        mock_print.assert_called_once_with("Failed to execute action: API Error")


class TestApplyRules(unittest.TestCase):

    @patch('rule_filter_client.authenticate_gmail_api')
    @patch('rule_filter_client.open', new_callable=mock_open, read_data='[{"conditions": {"match": "all", "rules": []}, "actions": []}]')
    def test_rules_json_accessed(self, mock_open_file, mock_authenticate_gmail_api):
        apply_rules()
        mock_open_file.assert_called_once_with('rules.json', 'r')

    @patch('rule_filter_client.authenticate_gmail_api')
    @patch('rule_filter_client.open', new_callable=mock_open, read_data='[{"conditions": {"match": "all", "rules": []}, "actions": []}]')
    def test_authenticate_gmail_api_called(self, mock_open_file, mock_authenticate_gmail_api):
        apply_rules()
        mock_authenticate_gmail_api.assert_called_once_with('write_token.json', ['https://www.googleapis.com/auth/gmail.modify'])

    @patch('rule_filter_client.authenticate_gmail_api')
    @patch('rule_filter_client.sqlite3.connect')
    @patch('rule_filter_client.open', new_callable=mock_open, read_data='[{"conditions": {"match": "all", "rules": []}, "actions": []}]')
    def test_sqlite_called(self, mock_open_file, mock_sqlite_connect, mock_authenticate_gmail_api):
        mock_conn = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        apply_rules()
        mock_sqlite_connect.assert_called_once_with('emails.db')
        mock_conn.cursor.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('rule_filter_client.authenticate_gmail_api')
    @patch('rule_filter_client.match_rule')
    @patch('rule_filter_client.sqlite3.connect')
    @patch('rule_filter_client.open', new_callable=mock_open, read_data='[{"conditions": {"match": "all", "rules": []}, "actions": []}]')
    def test_match_rule_called_correct_times(self, mock_open_file, mock_sqlite_connect, mock_match_rule, mock_authenticate_gmail_api):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.return_value = [('email_id_1', '{"payload": {}}'), ('email_id_2', '{"payload": {}}')]

        apply_rules()

        self.assertEqual(mock_match_rule.call_count, 2 * 1)  # 2 rows * 1 rule (from mocked rules.json)

    @patch('rule_filter_client.apply_actions')
    @patch('rule_filter_client.match_rule')
    @patch('rule_filter_client.sqlite3.connect')
    @patch('rule_filter_client.open', new_callable=mock_open, read_data='[{"conditions": {"match": "all", "rules": []}, "actions": []}]')
    @patch('rule_filter_client.authenticate_gmail_api')
    def test_apply_actions_called(self, mock_authenticate_gmail_api, mock_open_file, mock_sqlite_connect, mock_match_rule, mock_apply_actions):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.return_value = [('email_id_1', '{"payload": {}}'), ('email_id_2', '{"payload": {}}')]

        mock_match_rule.return_value = True

        mock_service = MagicMock()
        mock_authenticate_gmail_api.return_value = mock_service

        apply_rules()

        expected_calls = [
            call(mock_service, 'email_id_1', []),
            call(mock_service, 'email_id_2', [])
        ]
        mock_apply_actions.assert_has_calls(expected_calls, any_order=True)
        self.assertEqual(mock_apply_actions.call_count, 2)  # 2 emails, both matching



if __name__ == '__main__':
    unittest.main()
