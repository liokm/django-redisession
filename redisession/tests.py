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

    def test_decode_django12(self):
        "We don't support Django 1.2 ever."

    def test_delete(self):
        self.session.save()
        self.session.delete(self.session.session_key)
        self.assertFalse(self.session.exists(self.session.session_key))

    if not hasattr(SessionTestsMixin, 'test_session_key_is_read_only'):
        def test_session_key_is_read_only(self):
            def set_session_key(session):
                session.session_key = session._get_new_session_key()
            self.assertRaises(AttributeError, set_session_key, self.session)


class RedisHashSessionTests(RedisSessionTests):
    override_config = {
        'USE_HASH': True
    }
