import unittest
from unittest.mock import patch, MagicMock

from users.utils.db.mongo_adapter import MongoAdapter, DuplicateKeyError, PyMongoError


# pylint: disable=protected-access
class MongoAdapterTestCase(unittest.TestCase):

    def setUp(self):
        self.patches = []
        self.mocks = {}

        mongo_patch = patch('users.utils.db.mongo_adapter.MongoClient')
        self.mocks['mongo_mock'] = mongo_patch.start()
        self.patches.append(mongo_patch)

        conn_str = patch('users.utils.db.mongo_adapter.MONGO_CONNECTION_STRING',
                         new='mock_connection')
        self.mocks['conn_str'] = conn_str.start()
        self.patches.append(conn_str)

    def tearDown(self):
        for patch_ in self.patches:
            patch_.stop()

    def test_init_client_created(self):
        # Setup
        mock_self = MagicMock()

        # Act
        MongoAdapter.__init__(mock_self)

        # Assert
        self.mocks['mongo_mock'].assert_called_with(
            'mock_connection',
            connect=True
        )

    def test_create_successful_run(self):
        # Setup
        mock_self = MagicMock()
        collection = 'test'
        doc = {
            'username': 'unique_user',
            'name': 'chad'
        }
        mock_self.db_['test'].insert_one.return_value = MagicMock(
            acknowledged=True
        )
        mock_self.db_['test'].insert_one.side_effect = doc.update(
            _id='mongo_created_id'
        )

        # Act
        created = MongoAdapter.create(mock_self, collection, doc)

        # Assert
        mock_self.db_['test'].insert_one.assert_called_with(
            {'username': 'unique_user','name': 'chad'}
        )
        self.assertTrue(created)

    def test_create_doc_already_exists(self):
        # Setup
        mock_self = MagicMock()
        mock_self.db_['test'].insert_one.side_effect = DuplicateKeyError(MagicMock)
        collection = 'test'
        doc = {
            'username': 'unique_user',
            'name': 'chad'
        }

        # Act & Assert
        with self.assertRaises(KeyError):
            MongoAdapter.create(mock_self, collection, doc)

    @staticmethod
    def test_update_successful_run_updated_document():
        # Setup
        mock_self = MagicMock()
        collection = 'test'
        doc = {
            'username': 'unique_user',
            'password': 'ape',
            'test_field': 'new_value'
        }
        mock_self.db_['test'].update_one.return_value = MagicMock(
            matched_count=1
        )

        # Act
        MongoAdapter.update(mock_self, collection, doc)

        # Assert
        mock_self.db_['test'].update_one.assert_called_with(
            {'username': 'unique_user', 'password': 'ape'},
            {'$set': {
                'username': 'unique_user',
                'password': 'ape',
                'test_field': 'new_value'
            }
        }
        )
        mock_self.get_user_information.assert_called_with(
            'test', 'unique_user', 'ape'
        )

    def test_update_no_match_raises_key_error(self):
        # Setup
        mock_self = MagicMock()
        collection = 'test'
        doc = {
            'username': 'missingno',
            'password': '?',
            'test_field': 'new_value'
        }
        mock_self.db_['test'].update_one.return_value = MagicMock(
            matched_count=0
        )

        # Act & Assert
        with self.assertRaises(KeyError):
            MongoAdapter.update(mock_self, collection, doc)
            mock_self.get_user_information.assert_not_called_with()

    def test_update_except_pymongoerror(self):
        # Setup
        mock_self = MagicMock()
        collection = 'test'
        doc = {
            'username': 'unique_user',
            'password': 'ape',
            'test_field': 'new_value'
        }
        mock_self.db_['test'].update_one.side_effect = PyMongoError

        # Act & Assert
        with self.assertRaises(RuntimeError):
            MongoAdapter.update(mock_self, collection, doc)

    def test_delete_successful_run_deleted_document(self):
        # Setup
        mock_self = MagicMock()
        collection = 'test'
        doc = {'username': 'unique_deleted'}
        mock_self.db_['test'].delete_one.return_value = MagicMock(
            acknowledged=True
        )

        # Act
        deleted = MongoAdapter.delete(mock_self, collection, doc)

        # Assert
        mock_self.db_['test'].delete_one.assert_called_with(
            {'username': 'unique_deleted'}
        )
        self.assertTrue(deleted)

    def test_delete_except_pymongoerror(self):
        # Setup
        mock_self = MagicMock()
        collection = 'test'
        doc = {'username': 'super_xandao'}
        mock_self.db_['test'].delete_one.side_effect = PyMongoError

        # Act & Assert
        with self.assertRaises(RuntimeError):
            MongoAdapter.delete(mock_self, collection, doc)

    def test_find_called_with_query(self):
        # Setup
        mock_self = MagicMock()
        collection = 'test'
        query = {'field': 'match'}
        mock_self.db_['test'].find.return_value = [
            {'_id': 1, 'ketchup': 1},
            {'_id': 2, 'mostarda': 2},
            {'_id': 3, 'maionese': 3}
        ]

        # Act
        results = MongoAdapter._find(mock_self, collection, query)

        # Assert
        mock_self.db_['test'].find.assert_called_with({'field': 'match'})
        self.assertEqual(results, [
            {'ketchup': 1}, {'mostarda': 2}, {'maionese': 3}
        ])

    def test_get_user_information_returns_user_object(self):
        # Setup
        mock_self = MagicMock()
        collection = 'test_col'
        username = 'hendrix'
        password = 'high_priest_of_saturn'
        mock_self._find.return_value = [
            {'remaining': 'fields', 'password': 'gone'}
        ]

        # Act
        user = MongoAdapter.get_user_information(
            mock_self, collection, username, password
        )

        # Assert
        mock_self._find.assert_called_with(
            'test_col', {
                'username': 'hendrix',
                'password': 'high_priest_of_saturn'
            }
        )
        self.assertEqual(user, {'remaining': 'fields'})

    def test_get_user_information_raises_key_error(self):
        # Setup
        mock_self = MagicMock()
        collection = 'test_col'
        username = 'high_priest_of_saturn'
        password = 'son of earth and sky'
        mock_self._find.return_value = []

        # Act & Assert
        with self.assertRaises(KeyError):
            MongoAdapter.get_user_information(
                mock_self, collection, username, password
            )
