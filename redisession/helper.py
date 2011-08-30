from django.conf import settings
import redis

_connections = {}
def get_redis(conf_name='default'):
    """simple helper for getting global Redis connection instances"""
    if conf_name not in _connections:
        # refs redis.Redis for **v
        _connections[conf_name] = redis.Redis(**getattr(
            settings, 'REDIS_CONFIG', {'default': {}})[conf_name])
    return _connections[conf_name]
