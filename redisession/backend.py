"""
A redis backend for django session, support string and hash mode.
"""

import struct
import time
from django.conf import settings
from django.contrib.sessions.backends.base import pickle, CreateError, SessionBase
from django.utils.functional import wraps

conf = {
    'SERVER': {},
    'USE_HASH': True,
    'KEY_GENERATOR': lambda x: x.decode('hex'),
    'HASH_KEY_GENERATOR': lambda x: x[:4].decode('hex'),
    'COMPRESS_LIB': 'snappy',
    'COMPRESS_MIN_LENGTH': 400,
}
conf.update(getattr(settings, 'REDIS_SESSION_CONFIG', {}))

# key generators should be robust for some bad keys,
# for example, x='a', which fails x.decode('hex').
# Here simply return an abnormal key instead of extra logic in code.
def generator_wrapper(func):
    def _w(key):
        try:
            return func(key)
        except:
            # TODO: log?
            return 'POSSIBLE_BAD_KEY:%s' % key
    return wraps(func)(_w)

conf['KEY_GENERATOR'] = generator_wrapper(conf['KEY_GENERATOR'])
conf['HASH_KEY_GENERATOR'] = generator_wrapper(conf['HASH_KEY_GENERATOR'])

if isinstance(conf['SERVER'], dict):
    import redis
    get_redis = lambda x: redis.Redis(**x)
else:
    from redisession.helper import get_redis

if conf['COMPRESS_LIB']:
    from django.utils.importlib import import_module
    compress_lib = import_module(conf['COMPRESS_LIB'])

# TODO: flag for security verify?
FLAG_COMPRESSED = 1

class SessionStore(SessionBase):
    def __init__(self, session_key=None):
        self._redis = get_redis(conf['SERVER'])
        super(SessionStore, self).__init__(session_key)

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
            self.session_key = self._get_new_session_key()
            try:
                self.save(must_create=True)
            except CreateError:
                continue
            self.modified = True
            return
        raise RuntimeError("Unable to create a new session key.")

    if conf['USE_HASH']:
        def save(self, must_create=False):
            if must_create:
                func = self._redis.hsetnx
            else:
                func = self._redis.hset
            session_data = self.encode(self._get_session(no_load=must_create))
            expire_date = struct.pack('<i', time.time()+self.get_expiry_age())
            result = func(conf['HASH_KEY_GENERATOR'](self.session_key),
                          conf['KEY_GENERATOR'](self.session_key),
                          expire_date+session_data)
            if must_create and not result:
                raise CreateError

        def load(self):
            session_data = self._redis.hget(
                    conf['HASH_KEY_GENERATOR'](self.session_key),
                    conf['KEY_GENERATOR'](self.session_key))
            if session_data is not None:
                expire_date = struct.unpack('<i', session_data[:4])[0]
                if expire_date > time.time():
                    return self.decode(session_data[4:])
            self.create()
            return {}

        def exists(self, session_key):
            return self._redis.hexists(conf['HASH_KEY_GENERATOR'](session_key),
                                       conf['KEY_GENERATOR'](session_key))

        def delete(self, session_key=None):
            if session_key is None:
                if self._session_key is None:
                    return
                session_key = self._session_key
            self._redis.hdel(conf['HASH_KEY_GENERATOR'](session_key),
                             conf['KEY_GENERATOR'](session_key))

    else: # not conf['USE_HASH']
        def save(self, must_create=False):
            if must_create:
                func = self._redis.setnx
            else:
                func = self._redis.set
            key = conf['KEY_GENERATOR'](self.session_key)
            result = func(key, self.encode(self._get_session(no_load=must_create)))
            if must_create and not result:
                raise CreateError
            self._redis.expire(key, self.get_expiry_age())

        def load(self):
            session_data = self._redis.get(conf['KEY_GENERATOR'](self.session_key))
            if session_data is not None:
                return self.decode(session_data)
            self.create()
            return {}

        def exists(self, session_key):
            return self._redis.exists(conf['KEY_GENERATOR'](session_key))

        def delete(self, session_key=None):
            if session_key is None:
                if self._session_key is None:
                    return
                session_key = self._session_key
            self._redis.delete(conf['KEY_GENERATOR'](session_key))
