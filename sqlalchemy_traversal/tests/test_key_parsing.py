import unittest

class TestKeyParsing(unittest.TestCase):
    def test_limit_key_parsing(self):
        from sqlalchemy_traversal import parse_key

        keys = [
            "/messages.limit(0,20)"
            , "/messages.order_by.limit(2,20)"
        ]

        for key in keys:
            result = parse_key(key)
            import pdb; pdb.set_trace()
