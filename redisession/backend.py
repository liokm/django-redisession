"""
A redis backend for django session, support string and hash mode.
"""

import struct
import time
from django.conf import settings
from django.contrib.sessions.backends.base import pickle, CreateError, SessionBase

conf = {
    'SERVER': {},
    'USE_HASH': True,
    'KEY_GENERATOR': lambda x: x.decode('hex'),
    'HASH_KEY_GENERATOR': lambda x: x[:4].decode('hex'),
    'HASH_KEYS_CHECK_FOR_EXPIRY': lambda r: (reduce(lambda p,y :p.randomkey(),
        xrange(100), r.pipeline()).execute()),
    'COMPRESS_LIB': 'snappy',
    'COMPRESS_MIN_LENGTH': 400,
    'LOG_KEY_ERROR': False
}
# For session key contains '0-9a-z' in incoming Django 1.5
# conf['KEY_GENERATOR'] = lambda x: x.decode('base64')
# conf['HASH_KEY_GENERATOR'] = lambda x: x.decode('base64')[:2]
conf.update(getattr(settings, 'REDIS_SESSION_CONFIG', {}))

if conf['LOG_KEY_ERROR']:
    import logging
    logger = logging.getLogger('redisession')
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.WARNING)

if isinstance(conf['SERVER'], dict):
    class GetRedis(object):
        def __call__(self, conf):
            if not hasattr(self, '_redis'):
                import redis
                self._redis = redis.Redis(**conf)
            return self._redis
    get_redis = GetRedis()
else:
    from redisession.helper import get_redis

if conf['COMPRESS_LIB']:
    from django.utils.importlib import import_module
    compress_lib = import_module(conf['COMPRESS_LIB'])

# TODO: flag for security verification?
FLAG_COMPRESSED = 1

class SessionStore(SessionBase):
    def __init__(self, session_key=None):
        self._redis = get_redis(conf['SERVER'])
        super(SessionStore, self).__init__(session_key)

    # XXX Try to partially comply w/ session API of newer Django (>= 1.4) for Django 1.3
    # Instead of checking Django version, test the existence directly.
    if not hasattr(SessionBase, '_get_or_create_session_key'):
        session_key = property(SessionBase._get_session_key)

        def _get_or_create_session_key(self):
            if self._session_key is None:
                self._session_key = self._get_new_session_key()
            return self._session_key

    def encode(self, session_dict):
        data = pickle.dumps(session_dict, pickle.HIGHEST_PROTOCOL)
        flag = 0
        if conf['COMPRESS_LIB'] and len(data) >= conf['COMPRESS_MIN_LENGTH']:
            compressed = compress_lib.compress(data)
            if len(compressed) < len(data):
                flag |= FLAG_COMPRESSED
                data = compressed
        return chr(flag) + data

    def decode(self, session_data):
        flag, data = ord(session_data[:1]), session_data[1:]
        if flag & FLAG_COMPRESSED:
            if conf['COMPRESS_LIB']:
                return pickle.loads(compress_lib.decompress(data))
            raise ValueError('redisession: found compressed data without COMPRESS_LIB specified.')
        return pickle.loads(data)

    def create(self):
        for i in xrange(10000):
            self._session_key = self._get_new_session_key()
            try:
                self.save(must_create=True)
            except CreateError:
                continue
            self.modified = True
            return
        raise RuntimeError('Unable to create a new session key.')

    if conf['USE_HASH']:
        def _make_key(self, session_key):
            try:
                return (conf['HASH_KEY_GENERATOR'](session_key), conf['KEY_GENERATOR'](session_key))
            except:
                if conf['LOG_KEY_ERROR']:
                    logger.warning('misconfigured key-generator or bad key "%s"' % session_key)

        def save(self, must_create=False):
            if must_create:
                func = self._redis.hsetnx
            else:
                func = self._redis.hset
            session_data = self.encode(self._get_session(no_load=must_create))
            expire_date = struct.pack('>I', int(time.time()+self.get_expiry_age()))
            key = self._make_key(self._get_or_create_session_key())
            if key is None:
                # XXX must_create = True w/ bad key or misconfigured KEY_GENERATOR,
                # which has already been logged in _make_key.
                raise CreateError
            result = func(*key, value=expire_date+session_data)
            if must_create and not result:
                raise CreateError

        def load(self):
            key = self._make_key(self._get_or_create_session_key())
            if key is not None:
                session_data = self._redis.hget(*key)
                if session_data is not None:
                    expire_date = struct.unpack('>I', session_data[:4])[0]
                    if expire_date > time.time():
                        return self.decode(session_data[4:])
            self.create()
            return {}

        def exists(self, session_key):
            key = self._make_key(session_key)
            if key is not None:
                return self._redis.hexists(*key)
            return False

        def delete(self, session_key=None):
            if session_key is None:
                if self.session_key is None:
                    return
                session_key = self.session_key
            key = self._make_key(session_key)
            if key is not None:
                self._redis.hdel(*key)

    else: # not conf['USE_HASH']
        def _make_key(self, session_key):
            try:
                return conf['KEY_GENERATOR'](session_key)
            except:
                if conf['LOG_KEY_ERROR']:
                    logger.warning('misconfigured key-generator or bad key "%s"' % session_key)

        def save(self, must_create=False):
            pipe = self._redis.pipeline()
            if must_create:
                pipe = pipe.setnx
            else:
                pipe = pipe.set
            session_data = self.encode(self._get_session(no_load=must_create))
            key = self._make_key(self._get_or_create_session_key())
            if key is None:
                # XXX must_create = True w/ bad key or misconfigured KEY_GENERATOR,
                # which has already been logged in _make_key.
                raise CreateError
            result = pipe(key, session_data).expire(key, self.get_expiry_age()).execute()
            if must_create and not (result[0] and result[1]): # for Python 2.4 (Django 1.3)
                raise CreateError

        def load(self):
            key = self._make_key(self._get_or_create_session_key())
            if key is not None:
                session_data = self._redis.get(key)
                if session_data is not None:
                    return self.decode(session_data)
            self.create()
            return {}

        def exists(self, session_key):
            key = self._make_key(session_key)
            if key is not None:
                return key in self._redis
            return False

        def delete(self, session_key=None):
            if session_key is None:
                if self.session_key is None:
                    return
                session_key = self.session_key
            key = self._make_key(session_key)
            if key is not None:
                self._redis.delete(key)
