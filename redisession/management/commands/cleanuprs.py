import struct
import time
from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
    help = """Clean out expired sessions from redisession data."""
    def handle_noargs(self, **options):
        from redisession.backend import conf, get_redis
        # don't bother to check if hash mode is disabled
        if not conf['USE_HASH']:
            return
        r = get_redis(conf['SERVER'])
        now = struct.pack('>I', int(time.time()))
        pipe = r.pipeline()
        for hash_key in set(conf['HASH_KEYS_CHECK_FOR_EXPIRY'](r)):
            for f, v in r.hgetall(hash_key).iteritems():
                if v[:4] < now:
                    pipe = pipe.hdel(hash_key, f)
        pipe.execute()
