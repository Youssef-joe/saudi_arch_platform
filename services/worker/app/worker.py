from rq import Worker, Queue, Connection
import redis
from sima_shared.settings import settings

def main():
    conn = redis.Redis.from_url(settings.REDIS_URL)
    with Connection(conn):
        w = Worker([Queue("default")])
        w.work()

if __name__ == "__main__":
    main()
