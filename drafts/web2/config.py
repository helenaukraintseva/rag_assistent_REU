# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Базовые директории
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "outputs"

POLZA_API_KEY = os.environ.get('POLZA_API_KEY') or "pza_EOg9XmG-vdpv_AdKokT1ZfQhdJdpZxbS"
POLZA_API_URL = os.environ.get('POLZA_API_URL') or "https://api.polza.ai/api/v1"
POLZA_MODEL = os.environ.get('POLZA_MODEL') or "deepseek/deepseek-v3.2"

# Создаем необходимые директории
for directory in [OUTPUT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


class Config:
    """Основной класс конфигурации проекта"""

    # Секретный ключ для Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # База данных
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + str(BASE_DIR / 'ai_vuz.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }

    # Redis для кэширования и сессий
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'

    # Telegram Bot Token (из вашего файла)
    BOT_TOKEN = os.environ.get('BOT_TOKEN') or "8484924452:AAEAoqqybkTi88lEACfcHeTc0pczYSsiMwM"

    # Polza.ai API (из вашего файла)
    POLZA_API_KEY = os.environ.get('POLZA_API_KEY') or "pza_EOg9XmG-vdpv_AdKokT1ZfQhdJdpZxbS"
    POLZA_API_URL = os.environ.get('POLZA_API_URL') or "https://api.polza.ai/api/v1"
    POLZA_MODEL = os.environ.get('POLZA_MODEL') or "deepseek/deepseek-v3.2"

    # Файл для хранения данных (из вашего файла)
    DATA_FILE = BASE_DIR / "users_data.json"

    # Настройки векторной базы данных
    VECTOR_DB_CONFIG = {
        "chromadb": {
            "persist_directory": str(OUTPUT_DIR / "chroma_db"),
            "collection_name": "documents",
            "use_chromadb": True
        },
        "faiss": {
            "index_path": str(OUTPUT_DIR / "faiss_index.bin"),
            "metadata_path": str(OUTPUT_DIR / "metadata.pkl"),
            "use_chromadb": False
        }
    }

    # Выбор активной векторной БД
    VECTOR_DB_TYPE = os.environ.get('VECTOR_DB_TYPE', 'chromadb')

    # Настройки обработки текста
    CHUNK_SIZE = 1000  # Размер фрагмента в символах
    CHUNK_OVERLAP = 200  # Перекрытие между фрагментами

    # Настройки модели эмбеддингов
    EMBEDDING_MODEL = "cointegrated/LaBSE-en-ru"  # Русскоязычная модель
    EMBEDDING_DIM = 768  # Размерность векторов
    DEVICE = "cpu"  # "cuda" для GPU

    # Настройки сессий
    PERMANENT_SESSION_LIFETIME = 7  # дней
    SESSION_COOKIE_SECURE = False  # True в production с HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Загрузка файлов
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}


class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
                              'sqlite:///' + str(BASE_DIR / 'ai_vuz_dev.db')
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    """Конфигурация для тестирования"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
                              'sqlite:///' + str(BASE_DIR / 'ai_vuz_test.db')
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'postgresql://user:pass@localhost/ai_vuz_prod'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


# Словарь с конфигурациями
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}