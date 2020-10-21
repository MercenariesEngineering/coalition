import redis


def get_ping_db():
    red = redis.Redis(host="redis", port=6379, db=0)
    return red
