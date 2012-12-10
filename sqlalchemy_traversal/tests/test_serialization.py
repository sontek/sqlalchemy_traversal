from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import Integer
from sqlalchemy.types import UnicodeText
from sqlalchemy.types import Unicode
from sqlalchemy.types import Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy import Column

from sqlalchemy_traversal import JsonSerializableMixin

import unittest
import os

Base = declarative_base()
maker = sessionmaker()
session = scoped_session(maker)


class User(Base, JsonSerializableMixin):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(Unicode(10), nullable=False)
    description = Column(UnicodeText)
    is_active = Column(Boolean, default=False, nullable=False)
    comments = Column(Integer, default=0)


class TestSerialization(unittest.TestCase):

    def setUp(self):
        Base.query = session.query_property()

        self.user = User(
            name="ralphbean",
            description="Some guy",
            is_active=False,
            comments=3,
        )

    def test_basic_serialization(self):
        request = object()
        d = self.user.__json__(object())
        assert d == dict(
            description='Some guy',
            is_active=False,
            id=None,
            name='ralphbean',
            comments=3,
        )

    def test_integer_serialization(self):
        request = object()
        d = self.user.__json__(object())
        assert d['comments'] == 3
        assert type(d['comments']) == int

    def test_unicode_serialization(self):
        request = object()
        d = self.user.__json__(object())
        assert d['name'] == 'ralphbean'
        assert isinstance(d['name'], unicode)

    def test_boolean_serialization(self):
        request = object()
        d = self.user.__json__(object())
        assert d['is_active'] is False
        assert type(d['is_active']) == bool
