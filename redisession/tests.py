from django.conf import settings
from django.contrib.sessions.tests import SessionTestsMixin
from django.utils import unittest

class RedisSessionTests(SessionTestsMixin, unittest.TestCase):
    redis_session_config = {
        'SERVER': {'db':1},
        'USE_HASH': False
    }
    def setUp(self):
        settings.REDIS_SESSION_CONFIG = self.redis_session_config
        from redisession.backend import SessionStore
        self.backend = SessionStore
        self.session = self.backend()

    def tearDown(self):
        super(RedisSessionTests, self).tearDown()

class RedisHashSessionTests(RedisSessionTests):
    redis_session_config = {
        'SERVER': {'db':2},
        'USE_HASH': True
    }
