# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_caching import Cache
from flask_cors import CORS
import redis
import os

db = SQLAlchemy()
migrate = Migrate()
cache = Cache()
cors = CORS()

# Redis для кэширования и сессий
try:
    redis_client = redis.Redis(
        host=os.environ.get('REDIS_HOST', 'localhost'),
        port=int(os.environ.get('REDIS_PORT', 6379)),
        db=int(os.environ.get('REDIS_DB', 0)),
        decode_responses=True,
        socket_connect_timeout=2  # Таймаут для избежания блокировки
    )
    # Проверка соединения
    redis_client.ping()
except Exception as e:
    print(f"Redis connection failed: {e}")
    redis_client = None