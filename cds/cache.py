import logging

log = logging.getLogger(__name__)

class SilentRedisCache(object):
    def __init__(self, cache):
        self.cache = cache

    def _safe_call(self, method_name, default, *args, **kwargs):
        try:
            return getattr(self.cache, method_name)(*args, **kwargs)
        except Exception as e:
            log.warning("Cache %s failed: %s", method_name, e)
            return default

    def get(self, *args, **kwargs): return self._safe_call('get', None, *args, **kwargs)
    def set(self, *args, **kwargs): return self._safe_call('set', False, *args, **kwargs)
    def add(self, *args, **kwargs): return self._safe_call('add', False, *args, **kwargs)
    def delete(self, *args, **kwargs): return self._safe_call('delete', False, *args, **kwargs)
    def has(self, *args, **kwargs): return self._safe_call('has', False, *args, **kwargs)
    def get_many(self, *args, **kwargs): return self._safe_call('get_many', [None]*len(args), *args, **kwargs)
    def set_many(self, *args, **kwargs): return self._safe_call('set_many', False, *args, **kwargs)
    def delete_many(self, *args, **kwargs): return self._safe_call('delete_many', False, *args, **kwargs)
    def clear(self, *args, **kwargs): return self._safe_call('clear', False, *args, **kwargs)
    def inc(self, *args, **kwargs): return self._safe_call('inc', None, *args, **kwargs)
    def dec(self, *args, **kwargs): return self._safe_call('dec', None, *args, **kwargs)

def silent_redis_cache(app, config, args, kwargs):
    from flask_caching.backends.rediscache import redis
    
    # Use the default flask_caching redis factory
    cache_instance = redis(app, config, args, kwargs)
    return SilentRedisCache(cache_instance)

def SilentImageRedisCache(app):
    try:
        from flask_iiif.cache.redis import ImageRedisCache
        class _SilentImageRedisCache(ImageRedisCache):
            def get(self, *args, **kwargs):
                try:
                    return super(_SilentImageRedisCache, self).get(*args, **kwargs)
                except Exception as e:
                    log.warning("IIIF Cache GET failed: %s", e)
                    return None
            def set(self, *args, **kwargs):
                try:
                    return super(_SilentImageRedisCache, self).set(*args, **kwargs)
                except Exception as e:
                    log.warning("IIIF Cache SET failed: %s", e)
                    return False
            def delete(self, *args, **kwargs):
                try:
                    return super(_SilentImageRedisCache, self).delete(*args, **kwargs)
                except Exception as e:
                    log.warning("IIIF Cache DELETE failed: %s", e)
                    return False
        return _SilentImageRedisCache(app)
    except ImportError:
        return None
