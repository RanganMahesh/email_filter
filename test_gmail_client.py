import unittest
from unittest.mock import patch, MagicMock
from gmail_client import authenticate_gmail_api, fetch_emails, store_emails_in_sqlite


class TestAuthenticateGmailAPI(unittest.TestCase):

    @patch('gmail_client.os.path.exists')
    @patch('gmail_client.Credentials.from_authorized_user_file')
    @patch('gmail_client.build')
    def test_token_storage(self, mock_build, mock_from_authorized_user_file, mock_exists):
        mock_exists.return_value = True
        mock_from_authorized_user_file.return_value = MagicMock()

        authenticate_gmail_api(['https://www.googleapis.com/auth/gmail.readonly'])

        mock_exists.assert_called_once_with('token.json')
        mock_from_authorized_user_file.assert_called_once_with('token.json',
                                                               ['https://www.googleapis.com/auth/gmail.readonly'])

    @patch('gmail_client.os.path.exists')
    @patch('gmail_client.Credentials.from_authorized_user_file')
    @patch('gmail_client.Request')
    @patch('gmail_client.build')
    def test_refresh_token(self, mock_build, mock_request, mock_from_authorized_user_file, mock_exists):
        mock_exists.return_value = True
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = 'token'
        mock_from_authorized_user_file.return_value = mock_creds
        mock_request_instance = MagicMock()
        mock_request.return_value = mock_request_instance

        authenticate_gmail_api(['https://www.googleapis.com/auth/gmail.readonly'])

        mock_creds.refresh.assert_called_once_with(mock_request_instance)

    @patch('gmail_client.os.path.exists')
    @patch('gmail_client.Credentials.from_authorized_user_file')
    @patch('gmail_client.InstalledAppFlow.from_client_secrets_file')
    @patch('gmail_client.build')
    def test_authentication_success(self, mock_build, mock_from_client_secrets_file,
                                                            mock_from_authorized_user_file, mock_exists):
        mock_exists.return_value = False
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_from_authorized_user_file.side_effect = Exception("No valid credentials")
        mock_flow = MagicMock()
        mock_from_client_secrets_file.return_value = mock_flow

        authenticate_gmail_api(['https://www.googleapis.com/auth/gmail.readonly'])

        mock_from_client_secrets_file.assert_called_once_with('credentials.json',
                                                              ['https://www.googleapis.com/auth/gmail.readonly'])
        mock_flow.run_local_server.assert_called_once_with(port=0, prompt='consent')

    @patch('gmail_client.os.path.exists')
    @patch('gmail_client.Credentials.from_authorized_user_file')
    @patch('gmail_client.InstalledAppFlow.from_client_secrets_file')
    @patch('gmail_client.build')
    def test_authentication_failure(self, mock_build, mock_from_client_secrets_file, mock_from_authorized_user_file,
                                    mock_exists):
        mock_exists.return_value = False
        mock_from_authorized_user_file.side_effect = Exception("Error loading token")
        mock_from_client_secrets_file.side_effect = Exception("Error creating flow")

        service = authenticate_gmail_api(['https://www.googleapis.com/auth/gmail.readonly'])

        self.assertIsNone(service)

    @patch('gmail_client.os.path.exists')
    @patch('gmail_client.Credentials.from_authorized_user_file')
    @patch('gmail_client.InstalledAppFlow.from_client_secrets_file')
    @patch('gmail_client.build')
    def test_build_success(self, mock_build, mock_from_client_secrets_file, mock_from_authorized_user_file, mock_exists):
        mock_exists.return_value = True
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_from_authorized_user_file.return_value = mock_creds

        authenticate_gmail_api(['https://www.googleapis.com/auth/gmail.readonly'])

        mock_build.assert_called_once_with('gmail', 'v1', credentials=mock_creds)

    @patch('gmail_client.os.path.exists')
    @patch('gmail_client.Credentials.from_authorized_user_file')
    @patch('gmail_client.InstalledAppFlow.from_client_secrets_file')
    @patch('gmail_client.build')
    def test_build_failure(self, mock_build, mock_from_client_secrets_file, mock_from_authorized_user_file,
                           mock_exists):
        mock_exists.return_value = True
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_from_authorized_user_file.return_value = mock_creds
        mock_build.side_effect = Exception("Error building service")

        service = authenticate_gmail_api(['https://www.googleapis.com/auth/gmail.readonly'])

        self.assertIsNone(service)


class TestFetchEmails(unittest.TestCase):

    @patch('gmail_client.authenticate_gmail_api')
    def test_authenticate_gmail_api_called(self, mock_authenticate_gmail_api):
        mock_service = MagicMock()
        mock_authenticate_gmail_api.return_value = mock_service

        fetch_emails()

        mock_authenticate_gmail_api.assert_called_once_with(['https://www.googleapis.com/auth/gmail.readonly'])

    @patch('gmail_client.authenticate_gmail_api')
    def test_list_and_get_called(self, mock_authenticate_gmail_api):
        # Mock the Gmail service and its methods
        mock_service = MagicMock()
        mock_authenticate_gmail_api.return_value = mock_service
        mock_list = mock_service.users().messages().list.return_value
        mock_get = mock_service.users().messages().get.return_value

        mock_list.execute.return_value = {
            'messages': [{'id': 'msg1'}, {'id': 'msg2'}]
        }

        mock_get.execute.side_effect = lambda: {'id': 'msg1', 'payload': {}}

        fetch_emails()

        mock_service.users().messages().list.assert_called_once_with(userId='me', maxResults=10, q='')
        mock_service.users().messages().get.assert_any_call(userId='me', id='msg1')
        mock_service.users().messages().get.assert_any_call(userId='me', id='msg2')

    @patch('gmail_client.authenticate_gmail_api')
    @patch('builtins.print')
    def test_list_exception(self, mock_print, mock_authenticate_gmail_api):
        mock_service = MagicMock()
        mock_authenticate_gmail_api.return_value = mock_service
        mock_list = mock_service.users().messages().list.return_value
        mock_list.execute.side_effect = Exception("Error fetching messages")

        fetch_emails()

        mock_print.assert_called_with("Failed to fetch email: Error fetching messages")

    @patch('gmail_client.authenticate_gmail_api')
    @patch('builtins.print')
    def test_get_exception(self, mock_print, mock_authenticate_gmail_api):
        mock_service = MagicMock()
        mock_authenticate_gmail_api.return_value = mock_service
        mock_list = mock_service.users().messages().list.return_value
        mock_get = mock_service.users().messages().get.return_value

        mock_list.execute.return_value = {'messages': [{'id': 'msg1'}]}

        mock_get.execute.side_effect = Exception("Error fetching message data")

        fetch_emails()

        mock_print.assert_called_with("Failed to fetch email: Error fetching message data")


class TestStoreEmailsInSQLite(unittest.TestCase):

    @patch('sqlite3.connect')
    def test_store_emails_in_sqlite(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        emails = [
            {'id': 'msg1', 'payload': {'headers': [{'name': 'Subject', 'value': 'Test Subject'}]}},
            {'id': 'msg2', 'payload': {'headers': [{'name': 'Subject', 'value': 'Another Test'}]}}
        ]

        store_emails_in_sqlite(emails)

        mock_connect.assert_called_once_with('emails.db')

        mock_cursor.execute.assert_any_call('CREATE TABLE IF NOT EXISTS emails (id TEXT PRIMARY KEY, payload TEXT)')

        mock_cursor.execute.assert_any_call("INSERT OR REPLACE INTO emails (id, payload) VALUES (?, ?)",
                                            ('msg1', '{"headers": [{"name": "Subject", "value": "Test Subject"}]}'))
        mock_cursor.execute.assert_any_call("INSERT OR REPLACE INTO emails (id, payload) VALUES (?, ?)",
                                            ('msg2', '{"headers": [{"name": "Subject", "value": "Another Test"}]}'))

        mock_conn.commit.assert_called_once()

        mock_conn.close.assert_called_once()

    @patch('sqlite3.connect')
    def test_sqlite_exception_handling(self, mock_connect):
        # Create a mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        emails = [{'id': 'msg1', 'payload': {}}]

        mock_cursor.execute.side_effect = Exception("SQL Error")

        with patch('builtins.print') as mock_print:
            store_emails_in_sqlite(emails)

            mock_print.assert_called_with("An error occurred while updating the DB: SQL Error")


if __name__ == '__main__':
    unittest.main()
