"""
simple helper for holding redis connection instances, no connection pool support.
"""

from django.conf import settings
import redis

# refs redis.Redis for **v
_connections = dict((k, redis.Redis(**v)) for k,v in \
        getattr(settings, 'REDIS_CONF', {'default': {}}).iteritems())
def get_redis(conf_name='default'):
    return _connections[conf_name]
