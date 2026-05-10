"""
Конфигурация проекта векторной базы данных.
"""

import os
from pathlib import Path

auto_key = "NmU3NTliZmMtYWZmZi00NjgzLWFkZjQtYmYxZTdlN2ExNTdjOjc0NjNlMzhmLTIwYjMtNGRkZi1hNDIzLTIxYzdmZGE4OTJlMQ=="

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = "8484924452:AAEAoqqybkTi88lEACfcHeTc0pczYSsiMwM"

# Polza.ai API
POLZA_API_KEY = "pza_EOg9XmG-vdpv_AdKokT1ZfQhdJdpZxbS"
POLZA_API_URL = "https://api.polza.ai/api/v1"
POLZA_MODEL = "deepseek/deepseek-v3.2"

# Файл для хранения данных
DATA_FILE = "users_data.json"


BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "rag_vector_db/outputs"

VECTOR_DB_CONFIG = {
    "chromadb": {
        "persist_directory": OUTPUT_DIR / "chroma_db",
        "collection_name": "documents",
        "use_chromadb": True
    },
    "faiss": {
        "index_path": OUTPUT_DIR / "faiss_index.bin",
        "metadata_path": OUTPUT_DIR / "metadata.pkl",
        "use_chromadb": False
    },
    "pinecone": {
        "api_key": os.getenv("PINECONE_API_KEY", "pcsk_2xUgtz_3i4U6wkr9hQVHHLVxi5Ua2njeQVvT8whwrmatJ52RBmwvTBawVFmfAAnGGWwwxU"),
        "environment": "us-east1-gcp",
        "index_name": "university-docs",
        "dimension": 768,
        "metric": "cosine"
    }
}


class Config:
    """Класс конфигурации проекта"""

    # Пути к директориям
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data"
    RAW_DATA_DIR = DATA_DIR / "raw"
    PROCESSED_DATA_DIR = DATA_DIR / "processed"
    OUTPUT_DIR = BASE_DIR / "rag_vector_db/outputs"

    CHROMA_PERSIST_DIR = OUTPUT_DIR / "chroma_db"
    CHROMA_COLLECTION_NAME = "documents"

    VECTOR_DB = "chromadb"  # или "faiss"

    # Создание директорий при инициализации
    def __init__(self):
        for directory in [self.DATA_DIR, self.RAW_DATA_DIR,
                          self.PROCESSED_DATA_DIR, self.OUTPUT_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

    # Настройки обработки текста
    CHUNK_SIZE = 1000  # Размер фрагмента в символах
    CHUNK_OVERLAP = 200  # Перекрытие между фрагментами

    # Настройки модели эмбеддингов
    EMBEDDING_MODEL = "cointegrated/LaBSE-en-ru"  # Русскоязычная модель
    EMBEDDING_DIM = 768  # Размерность векторов
    DEVICE = "cpu"  # "cuda" для GPU

    # Настройки FAISS
    @property
    def FAISS_INDEX_PATH(self):
        return self.OUTPUT_DIR / "faiss_index.bin"

    @property
    def METADATA_PATH(self):
        return self.OUTPUT_DIR / "metadata.pkl"


# Создаем глобальный экземпляр конфигурации

AUTH_KEY = "6e759bfc-afff-4683-adf4-bf1e7e7a157c"  # В формате "ключ:секрет"
SCOPE = "GIGACHAT_API_PERS" # Для доступа к модели GigaChat
MY_AUTH_KEY = "NmU3NTliZmMtYWZmZi00NjgzLWFkZjQtYmYxZTdlN2ExNTdjOjg0OThkMGM2LWNiMWQtNGIyZi1iMzQyLTZkYzkxNzkxYmU1ZA=="