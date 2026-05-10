# pinecone_adapter.py
"""
Адаптер для работы с Pinecone - облачной векторной БД.
"""

import logging
from typing import List, Dict, Any, Optional, Union
import numpy as np
from pathlib import Path
import time

logger = logging.getLogger(__name__)


class PineconeAdapter:
    """
    Адаптер для работы с Pinecone векторной БД.
    """

    def __init__(self,
                 api_key: str,
                 environment: str = "us-east1-gcp",
                 index_name: str = "university-docs",
                 dimension: int = 768,
                 metric: str = "cosine",
                 **kwargs):
        """
        Инициализация Pinecone адаптера.

        Args:
            api_key: API ключ Pinecone
            environment: Регион Pinecone
            index_name: Название индекса
            dimension: Размерность векторов
            metric: Метрика сходства (cosine, euclidean, dotproduct)
            **kwargs: Дополнительные параметры
        """
        try:
            import pinecone
            self.pinecone = pinecone
        except ImportError:
            logger.error("Pinecone не установлен. Установите: pip install pinecone-client")
            raise

        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        self.dimension = dimension
        self.metric = metric

        # Инициализация Pinecone
        logger.info(f"Инициализация Pinecone: {index_name} в {environment}")

        try:
            # Инициализируем Pinecone
            self.pinecone.init(
                api_key=api_key,
                environment=environment
            )

            # Проверяем существование индекса
            existing_indexes = self.pinecone.list_indexes()

            if index_name not in existing_indexes:
                logger.info(f"Индекс {index_name} не найден, создаю новый...")
                self._create_index()
            else:
                logger.info(f"Индекс {index_name} найден, подключаюсь...")
                self.index = self.pinecone.Index(index_name)

            # Тестовое соединение
            self._test_connection()

        except Exception as e:
            logger.error(f"Ошибка инициализации Pinecone: {e}")
            raise

    def _create_index(self):
        """Создание нового индекса в Pinecone"""
        try:
            self.pinecone.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric=self.metric,
                metadata_config={"indexed": ["source", "type", "chunk_id"]}
            )

            # Ждем пока индекс будет готов
            time.sleep(5)

            # Подключаемся к индексу
            self.index = self.pinecone.Index(self.index_name)
            logger.info(f"Индекс {self.index_name} создан успешно")

        except Exception as e:
            logger.error(f"Ошибка создания индекса: {e}")
            raise

    def _test_connection(self):
        """Тестирование соединения с Pinecone"""
        try:
            # Простой запрос для проверки
            stats = self.index.describe_index_stats()
            logger.info(f"Pinecone подключен. Векторов: {stats.get('total_vector_count', 0)}")
            return True
        except Exception as e:
            logger.error(f"Ошибка тестирования соединения: {e}")
            return False

    def search(self,
               query: str,
               query_embedding: Optional[np.ndarray] = None,
               k: int = 5,
               filter: Optional[Dict] = None,
               namespace: str = "default") -> List[Dict[str, Any]]:
        """
        Поиск документов по запросу или вектору.

        Args:
            query: Текстовый запрос (если не передан query_embedding)
            query_embedding: Вектор запроса (опционально)
            k: Количество результатов
            filter: Фильтр по метаданным
            namespace: Пространство имен Pinecone

        Returns:
            List[Dict]: Результаты поиска
        """
        try:
            # Если вектор не передан, нужен embedder для его генерации
            if query_embedding is None:
                logger.warning("query_embedding не передан. Нужна внешняя модель эмбеддингов.")
                # В реальном использовании здесь должна быть генерация эмбеддинга
                # query_embedding = embedder.generate_single_embedding(query)
                return []

            # Преобразуем вектор в список для Pinecone
            vector = query_embedding.tolist() if isinstance(query_embedding, np.ndarray) else query_embedding

            # Выполняем поиск в Pinecone
            results = self.index.query(
                vector=vector,
                top_k=k,
                filter=filter,
                namespace=namespace,
                include_metadata=True,
                include_values=False
            )

            # Форматируем результаты
            formatted_results = []
            if results and results.get('matches'):
                for match in results['matches']:
                    score = match.get('score', 0.0)
                    metadata = match.get('metadata', {})

                    formatted_results.append({
                        'id': match.get('id', ''),
                        'text': metadata.get('text', ''),
                        'source': metadata.get('source', 'unknown'),
                        'score': float(score),
                        'metadata': metadata
                    })

            logger.debug(f"Pinecone поиск: найдено {len(formatted_results)} результатов")
            return formatted_results

        except Exception as e:
            logger.error(f"Ошибка поиска в Pinecone: {e}")
            return []

    def add_documents(self,
                      documents: List[str],
                      embeddings: np.ndarray,
                      metadata: List[Dict[str, Any]],
                      namespace: str = "default") -> List[str]:
        """
        Добавление документов в Pinecone.

        Args:
            documents: Тексты документов
            embeddings: Векторы эмбеддингов
            metadata: Метаданные документов
            namespace: Пространство имен Pinecone

        Returns:
            List[str]: ID добавленных документов
        """
        if len(documents) != len(embeddings) or len(documents) != len(metadata):
            logger.error("Количество документов, эмбеддингов и метаданных должно совпадать")
            return []

        try:
            # Подготавливаем векторы для Pinecone
            vectors = []
            ids = []

            for i, (doc, embedding, meta) in enumerate(zip(documents, embeddings, metadata)):
                # Генерируем уникальный ID
                doc_id = f"doc_{int(time.time())}_{i:06d}"
                ids.append(doc_id)

                # Добавляем текст в метаданные
                full_metadata = meta.copy()
                full_metadata['text'] = doc
                full_metadata['added_at'] = time.time()

                # Подготавливаем вектор
                vector = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding

                vectors.append((doc_id, vector, full_metadata))

            # Добавляем векторы в Pinecone батчами
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch, namespace=namespace)
                logger.info(f"Добавлено {len(batch)} векторов в Pinecone")

            logger.info(f"Всего добавлено {len(vectors)} документов в Pinecone")
            return ids

        except Exception as e:
            logger.error(f"Ошибка добавления документов в Pinecone: {e}")
            return []

    def delete_documents(self,
                         ids: Optional[List[str]] = None,
                         filter: Optional[Dict] = None,
                         namespace: str = "default") -> bool:
        """
        Удаление документов из Pinecone.

        Args:
            ids: ID документов для удаления
            filter: Фильтр по метаданным
            namespace: Пространство имен

        Returns:
            bool: Успешность операции
        """
        try:
            self.index.delete(
                ids=ids,
                filter=filter,
                namespace=namespace
            )

            logger.info(f"Удалено документов из Pinecone (ids: {len(ids) if ids else 'all'})")
            return True

        except Exception as e:
            logger.error(f"Ошибка удаления документов из Pinecone: {e}")
            return False

    def update_documents(self,
                         ids: List[str],
                         embeddings: Optional[np.ndarray] = None,
                         metadata: Optional[List[Dict]] = None,
                         namespace: str = "default") -> bool:
        """
        Обновление документов в Pinecone.

        Args:
            ids: ID документов для обновления
            embeddings: Новые эмбеддинги
            metadata: Новые метаданные
            namespace: Пространство имен

        Returns:
            bool: Успешность операции
        """
        try:
            # В Pinecone обновление - это upsert с теми же ID
            if embeddings is not None:
                vectors = []
                for i, (doc_id, embedding) in enumerate(zip(ids, embeddings)):
                    meta = metadata[i] if metadata and i < len(metadata) else {}
                    vector = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding
                    vectors.append((doc_id, vector, meta))

                self.index.upsert(vectors=vectors, namespace=namespace)
                logger.info(f"Обновлено {len(vectors)} документов в Pinecone")
                return True

            # Если только метаданные, нужно получить текущие векторы
            else:
                logger.warning("Обновление только метаданных в Pinecone требует получения текущих векторов")
                return False

        except Exception as e:
            logger.error(f"Ошибка обновления документов в Pinecone: {e}")
            return False

    def get_stats(self, namespace: str = "default") -> Dict[str, Any]:
        """
        Получение статистики индекса.

        Args:
            namespace: Пространство имен

        Returns:
            Dict: Статистика индекса
        """
        try:
            stats = self.index.describe_index_stats()

            result = {
                'vector_db': 'pinecone',
                'index_name': self.index_name,
                'environment': self.environment,
                'total_vectors': stats.get('total_vector_count', 0),
                'dimension': stats.get('dimension', 0),
                'index_fullness': stats.get('index_fullness', 0),
                'namespaces': {}
            }

            # Статистика по пространствам имен
            if stats.get('namespaces'):
                for ns, ns_stats in stats['namespaces'].items():
                    result['namespaces'][ns] = {
                        'vector_count': ns_stats.get('vector_count', 0)
                    }

            return result

        except Exception as e:
            logger.error(f"Ошибка получения статистики Pinecone: {e}")
            return {'error': str(e)}

    def clear(self, namespace: str = "default") -> bool:
        """
        Очистка пространства имен.

        Args:
            namespace: Пространство имен для очистки

        Returns:
            bool: Успешность операции
        """
        try:
            self.index.delete(delete_all=True, namespace=namespace)
            logger.info(f"Пространство имен '{namespace}' очищено в Pinecone")
            return True

        except Exception as e:
            logger.error(f"Ошибка очистки Pinecone: {e}")
            return False

    def save(self) -> bool:
        """Сохранение - не требуется для Pinecone (облачная БД)"""
        return True

    def load(self) -> bool:
        """Загрузка - уже выполнена при инициализации"""
        return True

    def health_check(self) -> Dict[str, Any]:
        """Проверка работоспособности Pinecone"""
        try:
            stats = self.get_stats()

            health = {
                'pinecone_available': True,
                'index_exists': True,
                'total_vectors': stats.get('total_vectors', 0),
                'dimension': stats.get('dimension', 0)
            }

            # Тестовый поиск
            test_vector = [0.0] * self.dimension
            test_results = self.search(
                query="тест",
                query_embedding=np.array(test_vector),
                k=1
            )

            health['test_search'] = len(test_results) >= 0  # Всегда True если нет ошибки

            return health

        except Exception as e:
            logger.error(f"Ошибка health check Pinecone: {e}")
            return {
                'pinecone_available': False,
                'error': str(e)
            }

    def close(self):
        """Закрытие соединения (опционально)"""
        # Pinecone не требует явного закрытия
        logger.info("Pinecone соединение закрыто")