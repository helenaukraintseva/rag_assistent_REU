"""
Управление ChromaDB векторной базой данных.
"""

import chromadb
from chromadb.config import Settings
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import logging
from pathlib import Path
import json
import uuid

logger = logging.getLogger(__name__)


class ChromaDBManager:
    """Класс для работы с ChromaDB"""

    def __init__(self,
                 persist_directory: str = "chroma_db",
                 collection_name: str = "documents",
                 embedding_function=None):
        """
        Инициализация менеджера ChromaDB.
        """
        if collection_name is None:
            collection_name = "documents"
            logger.warning(f"collection_name был None, установлено значение по умолчанию: {collection_name}")

        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.embedding_function = embedding_function

        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Определяем режим работы
        self.is_persistent = True  # или на основе параметров

        # Инициализируем клиент
        self.client = None
        self.collection = None


        self._initialize_client()

    def _initialize_client(self):
        """Инициализация клиента ChromaDB"""
        try:
            # НОВЫЙ способ с использованием PersistentClient
            if self.is_persistent and self.persist_directory:
                # Создаем директорию если ее нет
                self.persist_directory.mkdir(parents=True, exist_ok=True)

                # Используем PersistentClient для локального хранения
                self.client = chromadb.PersistentClient(
                    path=str(self.persist_directory),
                    settings=Settings(
                        anonymized_telemetry=False
                    )
                )
                logger.info(f"PersistentClient инициализирован: {self.persist_directory}")
            else:
                # Используем EphemeralClient для временного хранения в памяти
                self.client = chromadb.EphemeralClient()
                logger.info("EphemeralClient инициализирован (память)")

        except Exception as e:
            logger.error(f"Ошибка инициализации ChromaDB: {e}")
            raise

    def create_collection(self, collection_name: str = None, metadata: Dict = None):
        """
        Создание или получение коллекции.
        """
        if collection_name:
            self.collection_name = collection_name

        if self.collection_name is None:
            self.collection_name = "documents"
            logger.warning(f"collection_name был None, установлено значение по умолчанию: {self.collection_name}")

        try:
            # Удаляем существующую коллекцию с таким именем
            try:
                self.client.delete_collection(name=self.collection_name)
                logger.info(f"Существующая коллекция {self.collection_name} удалена")
            except Exception:
                pass  # Коллекция может не существовать

            # НОВЫЙ способ создания коллекции
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata=metadata or {"hnsw:space": "cosine"}
            )

            logger.info(f"Коллекция '{self.collection_name}' создана")
            return self.collection

        except Exception as e:
            logger.error(f"Ошибка создания коллекции: {e}")
            # Пробуем получить существующую коллекцию
            try:
                self.collection = self.client.get_collection(
                    name=self.collection_name
                )
                logger.info(f"Коллекция '{self.collection_name}' получена")
                return self.collection
            except Exception:
                raise

    def add_documents(self,
                      documents: List[str],
                      metadatas: List[Dict[str, Any]],
                      ids: Optional[List[str]] = None):
        """
        Добавление документов в коллекцию.

        Args:
            documents: Список текстов документов
            metadatas: Метаданные для каждого документа
            ids: ID документов (опционально)
        """
        if self.collection is None:
            self.create_collection()

        if not ids:
            ids = [str(uuid.uuid4()) for _ in range(len(documents))]

        try:
            # Добавляем документы
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(f"Добавлено {len(documents)} документов в коллекцию '{self.collection_name}'")
            return ids

        except Exception as e:
            logger.error(f"Ошибка добавления документов: {e}")
            raise

    def search(self,
               query_texts: List[str],
               n_results: int = 5,
               where: Optional[Dict] = None,
               **kwargs) -> Dict[str, List]:
        """
        Поиск документов.

        Args:
            query_texts: Тексты запросов
            n_results: Количество возвращаемых результатов
            where: Фильтр по метаданным
            **kwargs: Дополнительные параметры

        Returns:
            Dict: Результаты поиска
        """
        if self.collection is None:
            logger.error("Коллекция не создана")
            return {"documents": [], "metadatas": [], "distances": [], "ids": []}

        try:
            results = self.collection.query(
                query_texts=query_texts,
                n_results=n_results,
                where=where,
                **kwargs
            )

            logger.info(f"Поиск выполнен. Найдено результатов: {len(results.get('documents', [[]])[0])}")
            return results

        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return {"documents": [], "metadatas": [], "distances": [], "ids": []}

    def get_collection_info(self) -> Dict[str, Any]:
        """
        Получение информации о коллекции.

        Returns:
            Dict: Информация о коллекции
        """
        if self.collection is None:
            return {"status": "Коллекция не создана"}

        try:
            count = self.collection.count()

            # Получаем метаданные коллекции
            metadata = self.collection.metadata or {}

            return {
                "collection_name": self.collection_name,
                "total_documents": count,
                "persist_directory": str(self.persist_directory),
                "metadata": metadata,
                "embedding_function": "custom" if self.embedding_function else "default"
            }

        except Exception as e:
            return {"status": f"Ошибка получения информации: {e}"}

    def delete_documents(self, ids: List[str] = None, where: Dict = None):
        """
        Удаление документов из коллекции.

        Args:
            ids: ID документов для удаления
            where: Фильтр по метаданным для удаления
        """
        if self.collection is None:
            logger.error("Коллекция не создана")
            return False

        try:
            self.collection.delete(ids=ids, where=where)
            logger.info(f"Документы удалены")
            return True

        except Exception as e:
            logger.error(f"Ошибка удаления документов: {e}")
            return False

    def update_documents(self,
                         ids: List[str],
                         documents: List[str] = None,
                         metadatas: List[Dict] = None):
        """
        Обновление документов в коллекции.

        Args:
            ids: ID документов для обновления
            documents: Новые тексты документов
            metadatas: Новые метаданные
        """
        if self.collection is None:
            logger.error("Коллекция не создана")
            return False

        try:
            self.collection.update(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            logger.info(f"Документы {ids} обновлены")
            return True

        except Exception as e:
            logger.error(f"Ошибка обновления документов: {e}")
            return False

    def clear_collection(self):
        """Очистка коллекции"""
        try:
            self.client.delete_collection(name=self.collection_name)
            logger.info(f"Коллекция '{self.collection_name}' очищена")

            # Создаем заново
            self.create_collection()
            return True

        except Exception as e:
            logger.error(f"Ошибка очистки коллекции: {e}")
            return False

    def save(self):
        """Сохранение базы данных"""
        # ChromaDB автоматически сохраняет данные при использовании персистентного режима
        logger.info(f"База данных сохранена в {self.persist_directory}")
        return True

    def load(self):
        """Загрузка коллекции"""
        try:
            self.collection = self.client.get_collection(
                name=self.collection_name
            )
            logger.info(f"Коллекция '{self.collection_name}' загружена")
            return True

        except Exception as e:
            logger.error(f"Ошибка загрузки коллекции: {e}")
            return False


def get_embedding_function(model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    """
    Создание embedding function для ChromaDB с правильной сигнатурой.
    """
    try:
        from sentence_transformers import SentenceTransformer
        import chromadb.utils.embedding_functions as ef

        class SentenceTransformerEmbeddingFunction(ef.EmbeddingFunction):
            def __init__(self, model_name: str):
                self.model = SentenceTransformer(model_name)

            def __call__(self, input: List[str]) -> List[List[float]]:
                embeddings = self.model.encode(
                    input,
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )
                return embeddings.tolist()

        return SentenceTransformerEmbeddingFunction(model_name)

    except ImportError:
        logger.error("SentenceTransformers не установлен")
        return None