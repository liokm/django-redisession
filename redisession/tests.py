from django.conf import settings
from django.contrib.sessions.tests import SessionTestsMixin
from django.utils import unittest

conf = getattr(settings, 'REDIS_SESSION_CONFIG', {})

class RedisSessionTests(SessionTestsMixin, unittest.TestCase):
    override_config = {
        'USE_HASH': False
    }
    def setUp(self):
        test_conf = conf.copy()
        test_conf.update(self.override_config)
        settings.REDIS_SESSION_CONFIG = test_conf
        from redisession.backend import SessionStore
        self.backend = SessionStore
        self.session = self.backend()

    def tearDown(self):
        super(RedisSessionTests, self).tearDown()

class RedisHashSessionTests(RedisSessionTests):
    override_config = {
        'USE_HASH': True
    }
