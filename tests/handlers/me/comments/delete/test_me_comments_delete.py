import os
from unittest import TestCase
from me_comments_delete import MeCommentsDelete
from unittest.mock import patch, MagicMock
from tests_util import TestsUtil


class TestMeCommentsDelete(TestCase):
    dynamodb = TestsUtil.get_dynamodb_client()

    def setUp(self):
        TestsUtil.set_all_tables_name_to_env()
        TestsUtil.delete_all_tables(self.dynamodb)
        self.article_info_table = self.dynamodb.Table(os.environ['ARTICLE_INFO_TABLE_NAME'])
        self.article_info_items = [
            {
                'article_id': 'publicId0001',
                'user_id': 'article_user01',
                'status': 'public',
                'sort_key': 1520150272000000
            },
            {
                'article_id': 'publicId0002',
                'user_id': 'article_user02',
                'status': 'public',
                'sort_key': 1520150272000000
            }
        ]
        TestsUtil.create_table(self.dynamodb, os.environ['ARTICLE_INFO_TABLE_NAME'], self.article_info_items)

        self.comment_table = self.dynamodb.Table(os.environ['COMMENT_TABLE_NAME'])
        self.comment_items = [
            {
                'comment_id': 'comment00001',
                'article_id': 'publicId0001',
                'user_id': 'comment_user_01',
                'sort_key': 1520150272000000,
                'created_at': 1520150272,
                'text': 'コメントの内容1'
            },
            {
                'comment_id': 'comment00002',
                'article_id': 'publicId0002',
                'user_id': 'comment_user_02',
                'sort_key': 1520150272000001,
                'created_at': 1520150272,
                'text': 'コメントの内容2'
            },
            {
                'comment_id': 'comment00003',
                'article_id': 'publicId0002',
                'parent_id': 'comment00002',
                'user_id': 'comment_user_03',
                'sort_key': 1520150272000001,
                'created_at': 1520150272,
                'text': 'コメントの内容2'
            },
            {
                'comment_id': 'comment00004',
                'article_id': 'publicId0002',
                'parent_id': 'comment00002',
                'user_id': 'comment_user_04',
                'sort_key': 1520150272000001,
                'created_at': 1520150272,
                'text': 'コメントの内容2'
            }
        ]

        TestsUtil.create_table(self.dynamodb, os.environ['COMMENT_TABLE_NAME'], self.comment_items)

        self.deleted_comment_table = self.dynamodb.Table(os.environ['DELETED_COMMENT_TABLE_NAME'])
        deleted_comment_items = [
            {
                'comment_id': 'comment00003',
                'article_id': 'publicId0002',
                'user_id': 'comment_user_03',
                'sort_key': 1520150272000001,
                'created_at': 1520150272,
                'deleted_at': 1520160272,
                'text': 'コメントの内容2'
            }
        ]
        TestsUtil.create_table(self.dynamodb, os.environ['DELETED_COMMENT_TABLE_NAME'], deleted_comment_items)

    def tearDown(self):
        TestsUtil.delete_all_tables(self.dynamodb)

    def assert_bad_request(self, params):
        response = MeCommentsDelete(params, {}, self.dynamodb).main()

        self.assertEqual(response['statusCode'], 400)

    def test_main_ok(self):
        params = {
            'pathParameters': {
                'comment_id': self.comment_items[0]['comment_id']
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'cognito:username': 'comment_user_01',
                        'phone_number_verified': 'true',
                        'email_verified': 'true'
                    }
                }
            }
        }

        comment_before = self.comment_table.scan()['Items']
        deleted_comment_before = self.deleted_comment_table.scan()['Items']

        response = MeCommentsDelete(params, {}, self.dynamodb).main()

        comment_after = self.comment_table.scan()['Items']
        deleted_comment_after = self.deleted_comment_table.scan()['Items']

        comment = self.comment_table.get_item(Key={'comment_id': self.comment_items[0]['comment_id']}).get('Item')
        deleted_comment = self.deleted_comment_table.get_item(
            Key={'comment_id': self.comment_items[0]['comment_id']}).get('Item')

        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(len(comment_after) - len(comment_before), -1)
        self.assertEqual(len(deleted_comment_after) - len(deleted_comment_before), 1)
        self.assertIsNone(comment)
        for key, value in self.comment_items[0].items():
            self.assertEqual(deleted_comment[key], value)

    def test_main_ok_with_thread_comments(self):
        params = {
            'pathParameters': {
                'comment_id': self.comment_items[1]['comment_id']
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'cognito:username': 'article_user02',
                        'phone_number_verified': 'true',
                        'email_verified': 'true'
                    }
                }
            }
        }

        comment_before = self.comment_table.scan()['Items']
        deleted_comment_before = self.deleted_comment_table.scan()['Items']

        response = MeCommentsDelete(params, {}, self.dynamodb).main()

        comment_after = self.comment_table.scan()['Items']
        deleted_comment_after = self.deleted_comment_table.scan()['Items']

        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(len(comment_after) - len(comment_before), -3)
        self.assertEqual(len(deleted_comment_after) - len(deleted_comment_before), 2)

        for targets in [self.comment_items[1], self.comment_items[2], self.comment_items[3]]:
            comment = self.comment_table.get_item(Key={'comment_id': targets['comment_id']}).get('Item')
            deleted_comment = self.deleted_comment_table.get_item(
                Key={'comment_id': targets['comment_id']}).get('Item')

            self.assertIsNone(comment)
            for key, value in targets.items():
                self.assertEqual(deleted_comment[key], value)

    def test_main_ok_deleted_comment_exists(self):
        params = {
            'pathParameters': {
                'comment_id': self.comment_items[2]['comment_id']
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'cognito:username': 'comment_user_03',
                        'phone_number_verified': 'true',
                        'email_verified': 'true'
                    }
                }
            }
        }

        comment_before = self.comment_table.scan()['Items']
        deleted_comment_before = self.deleted_comment_table.scan()['Items']

        response = MeCommentsDelete(params, {}, self.dynamodb).main()

        comment_after = self.comment_table.scan()['Items']
        deleted_comment_after = self.deleted_comment_table.scan()['Items']

        comment = self.comment_table.get_item(Key={'comment_id': self.comment_items[2]['comment_id']}).get('Item')
        deleted_comment = self.deleted_comment_table.get_item(
            Key={'comment_id': self.comment_items[2]['comment_id']}).get('Item')

        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(len(comment_after) - len(comment_before), -1)
        self.assertEqual(len(deleted_comment_after) - len(deleted_comment_before), 0)
        self.assertIsNone(comment)
        for key, value in self.comment_items[2].items():
            self.assertEqual(deleted_comment[key], value)

    @patch('me_comments_delete.MeCommentsDelete._MeCommentsDelete__is_accessable_comment',
           MagicMock(return_value=False))
    def test_main_with_NotAuthorizedError(self):
        params = {
            'pathParameters': {
                'comment_id': self.comment_items[1]['comment_id']
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'cognito:username': 'comment_user_02',
                        'phone_number_verified': 'true',
                        'email_verified': 'true'
                    }
                }
            }
        }

        comment_before = self.comment_table.scan()['Items']
        deleted_comment_before = self.deleted_comment_table.scan()['Items']

        response = MeCommentsDelete(params, {}, self.dynamodb).main()

        comment_after = self.comment_table.scan()['Items']
        deleted_comment_after = self.deleted_comment_table.scan()['Items']

        self.assertEqual(response['statusCode'], 403)
        self.assertEqual(len(comment_after) - len(comment_before), 0)
        self.assertEqual(len(deleted_comment_after) - len(deleted_comment_before), 0)

    def test__is_accessable_comment_with_valid_article_user(self):
        params = {
            'pathParameters': {
                'comment_id': 'comment00001'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'cognito:username': 'article_user01',
                        'phone_number_verified': 'true',
                        'email_verified': 'true'
                    }
                }
            }
        }
        comment = self.comment_items[0]

        response = MeCommentsDelete(params, {}, self.dynamodb)._MeCommentsDelete__is_accessable_comment(comment)
        self.assertEqual(response, True)

    def test__is_accessable_comment_with_invalid_article_user(self):
        params = {
            'pathParameters': {
                'comment_id': 'comment00001'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'cognito:username': 'article_user02',
                        'phone_number_verified': 'true',
                        'email_verified': 'true'
                    }
                }
            }
        }
        comment = self.comment_items[0]

        response = MeCommentsDelete(params, {}, self.dynamodb)._MeCommentsDelete__is_accessable_comment(comment)
        self.assertEqual(response, False)

    def test__is_accessable_comment_with_valid_comment_user(self):
        params = {
            'pathParameters': {
                'comment_id': 'comment00001'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'cognito:username': 'comment_user_01',
                        'phone_number_verified': 'true',
                        'email_verified': 'true'
                    }
                }
            }
        }
        comment = self.comment_items[0]

        response = MeCommentsDelete(params, {}, self.dynamodb)._MeCommentsDelete__is_accessable_comment(comment)
        self.assertEqual(response, True)

    def test__is_accessable_comment_with_invalid_comment_user(self):
        params = {
            'pathParameters': {
                'comment_id': 'comment00001'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'cognito:username': 'comment_user_02',
                        'phone_number_verified': 'true',
                        'email_verified': 'true'
                    }
                }
            }
        }
        comment = self.comment_items[0]

        response = MeCommentsDelete(params, {}, self.dynamodb)._MeCommentsDelete__is_accessable_comment(comment)
        self.assertEqual(response, False)

    def test_call_get_validated_comment_existence(self):
        params = {
            'pathParameters': {
                'comment_id': 'comment00008'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'cognito:username': 'comment_user_01',
                        'phone_number_verified': 'true',
                        'email_verified': 'true'
                    }
                }
            }
        }

        mock_lib = MagicMock()
        with patch('me_comments_delete.DBUtil', mock_lib):
            MeCommentsDelete(params, {}, self.dynamodb).main()
            args, _ = mock_lib.get_validated_comment.call_args

            self.assertTrue(mock_lib.get_validated_comment.called)
            self.assertEqual(args[1], 'comment00008')

    def test_call_validate_article_existence(self):
        params = {
            'pathParameters': {
                'comment_id': 'comment00001'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'cognito:username': 'comment_user_01',
                        'phone_number_verified': 'true',
                        'email_verified': 'true'
                    }
                }
            }
        }

        mock_lib = MagicMock()
        with patch('me_comments_delete.DBUtil', mock_lib):
            mock_lib.get_validated_comment.return_value = self.comment_items[0]

            MeCommentsDelete(params, {}, self.dynamodb).main()
            args, kwargs = mock_lib.validate_article_existence.call_args

            self.assertTrue(mock_lib.validate_article_existence.called)
            self.assertTrue(args[0])
            self.assertEqual(args[1], 'publicId0001')
            self.assertEqual(kwargs['status'], 'public')

    def test_validation_comment_id_max(self):
        params = {
            'pathParameters': {
                'comment_id': 'A' * 13
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'cognito:username': 'like_user_01',
                        'phone_number_verified': 'true',
                        'email_verified': 'true'
                    }
                }
            }
        }
        self.assert_bad_request(params)
