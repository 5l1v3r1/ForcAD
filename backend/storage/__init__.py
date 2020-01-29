from contextlib import contextmanager

import aioredis
import redis
from psycopg2 import pool, extras

import config
from storage import (
    game,
    tasks,
    flags,
    caching,
    teams,
)

_redis_storage = None
_async_redis_pool = None
_db_pool = None


def get_db_pool():
    global _db_pool

    if not _db_pool:
        database_config = config.get_storage_config()['db']
        _db_pool = pool.SimpleConnectionPool(minconn=1, maxconn=20, **database_config)

    return _db_pool


@contextmanager
def db_cursor(dict_cursor=False):
    db_pool = get_db_pool()
    conn = db_pool.getconn()
    if dict_cursor:
        curs = conn.cursor(cursor_factory=extras.RealDictCursor)
    else:
        curs = conn.cursor()
    try:
        yield conn, curs
    finally:
        curs.close()
        db_pool.putconn(conn)


def get_redis_storage():
    global _redis_storage

    if not _redis_storage:
        redis_config = config.get_storage_config()['redis']
        _redis_storage = redis.StrictRedis(**redis_config)

    return _redis_storage


async def get_async_redis_pool(loop):
    global _async_redis_pool

    if not _async_redis_pool:
        redis_config = config.get_storage_config()['redis']
        address = f'redis://{redis_config["host"]}:{redis_config["port"]}'
        db = redis_config['db']
        _async_redis_pool = await aioredis.create_redis_pool(
            address=address,
            db=db,
            password=redis_config.get('password', None),
            minsize=5,
            maxsize=15,
            loop=loop,
        )
    return _async_redis_pool
