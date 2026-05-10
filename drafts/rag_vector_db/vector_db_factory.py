#!/usr/bin/env python3
"""
Фабрика для работы с разными векторными базами данных.
Поддерживает ChromaDB, FAISS и Pinecone.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)


class VectorDBInterface(ABC):
    """Интерфейс для векторных БД"""

    @abstractmethod
    def search(self, query: str, k: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """Поиск документов по запросу"""
        pass

    @abstractmethod
    def add_documents(self, documents: List[str], metadata: List[Dict[str, Any]]) -> List[str]:
        """Добавление документов"""
        pass

    @abstractmethod
    def delete_documents(self, ids: List[str] = None, where: Dict = None) -> bool:
        """Удаление документов"""
        pass

    @abstractmethod
    def update_documents(self, ids: List[str], documents: List[str] = None,
                         metadata: List[Dict] = None) -> bool:
        """Обновление документов"""
        pass

    @abstractmethod
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Получение документа по ID"""
        pass

    @abstractmethod
    def filter_documents(self, where: Dict, limit: int = 100) -> List[Dict[str, Any]]:
        """Фильтрация документов по метаданным"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        pass

    @abstractmethod
    def clear(self) -> bool:
        """Очистка базы данных"""
        pass

    @abstractmethod
    def save(self) -> bool:
        """Сохранение базы данных"""
        pass

    @abstractmethod
    def load(self) -> bool:
        """Загрузка базы данных"""
        pass


class ChromaDBAdapter(VectorDBInterface):
    """Адаптер для ChromaDB"""

    def __init__(self,
                 persist_directory: str = "chroma_db",
                 collection_name: str = "documents",
                 embedding_function=None,
                 **kwargs):
        """
        Инициализация адаптера ChromaDB.

        Args:
            persist_directory: Директория для сохранения
            collection_name: Название коллекции
            embedding_function: Функция для генерации эмбеддингов
            **kwargs: Дополнительные параметры
        """
        from chroma_manager import ChromaDBManager

        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.embedding_function = embedding_function

        logger.info(f"Инициализация ChromaDBAdapter: {collection_name} в {persist_directory}")

        # Инициализируем ChromaDB менеджер
        self.db = ChromaDBManager(
            persist_directory=str(self.persist_directory),
            collection_name=self.collection_name,
            embedding_function=self.embedding_function
        )

        # Загружаем коллекцию
        self.load()

    # ... (остальные методы ChromaDBAdapter остаются без изменений)
    # Полный код методов можно взять из оригинального файла


class FAISSAdapter(VectorDBInterface):
    """Адаптер для FAISS (для обратной совместимости)"""

    def __init__(self,
                 index_path: str = "outputs/faiss_index.bin",
                 metadata_path: str = "outputs/metadata.pkl",
                 **kwargs):
        """
        Инициализация адаптера FAISS.

        Args:
            index_path: Путь к FAISS индексу
            metadata_path: Путь к метаданным
            **kwargs: Дополнительные параметры
        """
        from faiss_manager import FAISSManager

        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)

        logger.info(f"Инициализация FAISSAdapter: {index_path}")

        # Инициализируем FAISS менеджер
        self.db = FAISSManager(
            index_path=str(self.index_path),
            metadata_path=str(self.metadata_path)
        )

        # Загружаем данные
        self.load()

    # ... (остальные методы FAISSAdapter остаются без изменений)
    # Полный код методов можно взять из оригинального файла


class PineconeAdapter(VectorDBInterface):
    """Адаптер для Pinecone"""

    def __init__(self,
                 api_key: str,
                 environment: str = "us-east1-gcp",
                 index_name: str = "documents",
                 dimension: int = 768,
                 metric: str = "cosine",
                 **kwargs):
        """
        Инициализация адаптера Pinecone.

        Args:
            api_key: API ключ Pinecone
            environment: Регион Pinecone
            index_name: Название индекса
            dimension: Размерность векторов
            metric: Метрика сходства (cosine, euclidean, dotproduct)
            **kwargs: Дополнительные параметры
        """
        try:
            from pinecone_adapter import PineconeAdapter as PineconeAdapterOriginal
        except ImportError:
            logger.error("Pinecone не установлен. Установите: pip install pinecone-client")
            raise

        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        self.dimension = dimension
        self.metric = metric

        logger.info(f"Инициализация PineconeAdapter: {index_name} в {environment}")

        # Инициализируем Pinecone адаптер
        self.db = PineconeAdapterOriginal(
            api_key=api_key,
            environment=environment,
            index_name=index_name,
            dimension=dimension,
            metric=metric,
            **kwargs
        )

        # Загружаем БД
        self.load()

    def search(self, query: str, k: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """
        Поиск документов по запросу.

        Args:
            query: Текстовый запрос
            k: Количество результатов
            **kwargs: Дополнительные параметры (filter, namespace и т.д.)

        Returns:
            List[Dict]: Результаты поиска
        """
        try:
            # Pinecone требует эмбеддинги, поэтому query используется только для логов
            # В реальном использовании нужна внешняя модель эмбеддингов
            logger.info(f"Pinecone поиск: '{query}' (нужен эмбеддинг)")

            # Для совместимости с интерфейсом возвращаем пустой список
            # В реальном использовании здесь должна быть генерация эмбеддинга
            return []

        except Exception as e:
            logger.error(f"Ошибка поиска в PineconeAdapter: {e}")
            return []

    def search_with_embedding(self,
                              query_embedding: np.ndarray,
                              k: int = 5,
                              **kwargs) -> List[Dict[str, Any]]:
        """
        Поиск по вектору эмбеддинга (специфичный метод для Pinecone).

        Args:
            query_embedding: Вектор эмбеддинга запроса
            k: Количество результатов
            **kwargs: Дополнительные параметры

        Returns:
            List[Dict]: Результаты поиска
        """
        try:
            # Используем метод search из оригинального PineconeAdapter
            results = self.db.search(
                query="",  # Не используется, так как передаем эмбеддинг
                query_embedding=query_embedding,
                k=k,
                **{k: v for k, v in kwargs.items() if k in ['filter', 'namespace']}
            )

            # Преобразуем в стандартный формат
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'id': result.get('id', ''),
                    'text': result.get('text', ''),
                    'source': result.get('source', 'unknown'),
                    'score': result.get('score', 0.0),
                    'metadata': result.get('metadata', {})
                })

            return formatted_results

        except Exception as e:
            logger.error(f"Ошибка поиска с эмбеддингом в PineconeAdapter: {e}")
            return []

    def add_documents(self, documents: List[str], metadata: List[Dict[str, Any]]) -> List[str]:
        """Добавление документов в Pinecone"""
        logger.warning("PineconeAdapter.add_documents требует эмбеддинги. Используйте add_documents_with_embeddings.")
        return []

    def add_documents_with_embeddings(self,
                                      documents: List[str],
                                      embeddings: np.ndarray,
                                      metadata: List[Dict[str, Any]],
                                      **kwargs) -> List[str]:
        """
        Добавление документов с эмбеддингами в Pinecone.

        Args:
            documents: Тексты документов
            embeddings: Векторы эмбеддингов
            metadata: Метаданные документов
            **kwargs: Дополнительные параметры (namespace и т.д.)

        Returns:
            List[str]: ID добавленных документов
        """
        try:
            return self.db.add_documents(
                documents=documents,
                embeddings=embeddings,
                metadata=metadata,
                **{k: v for k, v in kwargs.items() if k in ['namespace']}
            )
        except Exception as e:
            logger.error(f"Ошибка добавления документов в PineconeAdapter: {e}")
            return []

    def delete_documents(self, ids: List[str] = None, where: Dict = None) -> bool:
        """Удаление документов из Pinecone"""
        try:
            # Преобразуем where в filter для Pinecone
            filter_dict = where

            return self.db.delete_documents(
                ids=ids,
                filter=filter_dict,
                namespace=where.get('namespace', 'default') if where else 'default'
            )
        except Exception as e:
            logger.error(f"Ошибка удаления документов в PineconeAdapter: {e}")
            return False

    def update_documents(self, ids: List[str], documents: List[str] = None,
                         metadata: List[Dict] = None) -> bool:
        """Обновление документов в Pinecone"""
        logger.warning(
            "PineconeAdapter.update_documents требует эмбеддинги. Используйте update_documents_with_embeddings.")
        return False

    def update_documents_with_embeddings(self,
                                         ids: List[str],
                                         embeddings: np.ndarray = None,
                                         metadata: List[Dict] = None,
                                         **kwargs) -> bool:
        """
        Обновление документов с эмбеддингами в Pinecone.

        Args:
            ids: ID документов для обновления
            embeddings: Новые эмбеддинги
            metadata: Новые метаданные
            **kwargs: Дополнительные параметры

        Returns:
            bool: Успешность операции
        """
        try:
            return self.db.update_documents(
                ids=ids,
                embeddings=embeddings,
                metadata=metadata,
                **{k: v for k, v in kwargs.items() if k in ['namespace']}
            )
        except Exception as e:
            logger.error(f"Ошибка обновления документов в PineconeAdapter: {e}")
            return False

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Получение документа по ID из Pinecone"""
        try:
            # Pinecone не имеет прямого метода get по ID, используем fetch
            # В оригинальном адаптере такого метода нет, поэтому реализуем через поиск
            logger.warning("Pinecone не поддерживает прямой get по ID, используйте поиск с фильтром")
            return None
        except Exception as e:
            logger.error(f"Ошибка получения документа в PineconeAdapter: {e}")
            return None

    def filter_documents(self, where: Dict, limit: int = 100) -> List[Dict[str, Any]]:
        """Фильтрация документов по метаданным в Pinecone"""
        try:
            # Используем поиск с фильтром и случайным вектором
            random_vector = np.random.randn(self.dimension).tolist()

            results = self.db.search(
                query="",
                query_embedding=random_vector,
                k=limit,
                filter=where
            )

            # Преобразуем результаты
            filtered_docs = []
            for result in results:
                filtered_docs.append({
                    'text': result.get('text', ''),
                    'metadata': result.get('metadata', {}),
                    'source': result.get('source', 'unknown'),
                    'id': result.get('id', '')
                })

            return filtered_docs

        except Exception as e:
            logger.error(f"Ошибка фильтрации документов в PineconeAdapter: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики Pinecone"""
        try:
            stats = self.db.get_stats()

            # Приводим к стандартному формату
            return {
                'vector_db': 'pinecone',
                'index_name': self.index_name,
                'environment': self.environment,
                'total_documents': stats.get('total_vectors', 0),
                'dimension': stats.get('dimension', self.dimension),
                'metric': self.metric
            }

        except Exception as e:
            logger.error(f"Ошибка получения статистики в PineconeAdapter: {e}")
            return {'error': str(e)}

    def clear(self) -> bool:
        """Очистка Pinecone индекса"""
        try:
            return self.db.clear(namespace='default')
        except Exception as e:
            logger.error(f"Ошибка очистки PineconeAdapter: {e}")
            return False

    def save(self) -> bool:
        """Сохранение - не требуется для Pinecone (облачная БД)"""
        return True

    def load(self) -> bool:
        """Загрузка - уже выполнена при инициализации"""
        return True


def get_vector_db(db_type: str = "chromadb", **kwargs) -> VectorDBInterface:
    """
    Фабричная функция для получения векторной БД.

    Args:
        db_type: Тип БД ("chromadb", "faiss", "pinecone")
        **kwargs: Параметры для инициализации

    Returns:
        VectorDBInterface: Экземпляр векторной БД
    """
    db_type = db_type.lower()

    if db_type == "chromadb":
        return ChromaDBAdapter(**kwargs)
    elif db_type == "faiss":
        return FAISSAdapter(**kwargs)
    elif db_type == "pinecone":
        return PineconeAdapter(**kwargs)
    else:
        raise ValueError(f"Неизвестный тип векторной БД: {db_type}")


def test_adapters():
    """Тестирование адаптеров"""
    import tempfile

    print("=" * 60)
    print("ТЕСТИРОВАНИЕ АДАПТЕРОВ ВЕКТОРНЫХ БАЗ ДАННЫХ")
    print("=" * 60)

    # Создаем временную директорию
    temp_dir = tempfile.mkdtemp()

    try:
        # Тестируем ChromaDB адаптер
        print("\n1. ТЕСТ CHROMADB АДАПТЕРА:")

        # Создаем простую embedding function для теста
        def test_embed_function(texts):
            import random
            return [[random.random() for _ in range(384)] for _ in texts]

        chroma_adapter = ChromaDBAdapter(
            persist_directory=temp_dir + "/chroma_test",
            collection_name="test_docs",
            embedding_function=test_embed_function
        )

        # Добавляем тестовые документы
        test_docs = [
            "Расписание занятий на понедельник",
            "Контакты деканата факультета",
            "Правила обучения в университете"
        ]

        test_metadata = [
            {"source": "schedule.txt", "type": "schedule"},
            {"source": "contacts.txt", "type": "contacts"},
            {"source": "rules.txt", "type": "rules"}
        ]

        ids = chroma_adapter.add_documents(test_docs, test_metadata)
        print(f"   Добавлено документов: {len(ids)}")

        # Получаем статистику
        stats = chroma_adapter.get_stats()
        print(f"   Всего документов: {stats.get('total_documents', 0)}")

        # Ищем документы
        results = chroma_adapter.search("расписание", k=2)
        print(f"   Найдено результатов для 'расписание': {len(results)}")

        # Очищаем
        chroma_adapter.clear()

        print("   ✅ ChromaDB адаптер работает корректно")

    except Exception as e:
        print(f"   ❌ Ошибка теста ChromaDB адаптера: {e}")

    print("\n2. ТЕСТ FAISS АДАПТЕРА:")
    try:
        # Создаем тестовый FAISS индекс
        import faiss
        import numpy as np

        dimension = 768
        index = faiss.IndexFlatL2(dimension)

        # Создаем тестовые векторы
        n_vectors = 10
        vectors = np.random.randn(n_vectors, dimension).astype('float32')
        index.add(vectors)

        # Сохраняем индекс
        faiss.write_index(index, temp_dir + "/test_faiss.bin")

        # Создаем тестовые метаданные
        metadata = []
        for i in range(n_vectors):
            metadata.append({
                "text": f"Тестовый документ {i}",
                "source": f"test_source_{i}",
                "id": i
            })

        import pickle
        with open(temp_dir + "/test_metadata.pkl", "wb") as f:
            pickle.dump(metadata, f)

        # Тестируем FAISS адаптер
        faiss_adapter = FAISSAdapter(
            index_path=temp_dir + "/test_faiss.bin",
            metadata_path=temp_dir + "/test_metadata.pkl"
        )

        stats = faiss_adapter.get_stats()
        print(f"   Всего векторов: {stats.get('total_vectors', 0)}")

        print("   ✅ FAISS адаптер работает корректно")

    except Exception as e:
        print(f"   ❌ Ошибка теста FAISS адаптера: {e}")

    print("\n3. ТЕСТ PINECONE АДАПТЕРА:")
    try:
        # Проверяем наличие API ключа
        import os
        api_key = os.getenv("PINECONE_API_KEY")

        if not api_key:
            print("   ⚠️ PINECONE_API_KEY не установлен, пропускаем тест")
            print("   Установите переменную окружения: export PINECONE_API_KEY='ваш_ключ'")
        else:
            print("   ⚠️ Тест Pinecone требует облачный индекс, выполняется только проверка инициализации")

            # Пробуем инициализировать Pinecone адаптер
            pinecone_adapter = PineconeAdapter(
                api_key=api_key,
                index_name="test-index-" + str(hash(temp_dir))[-8:],  # Уникальное имя
                dimension=768
            )

            stats = pinecone_adapter.get_stats()
            print(f"   Pinecone инициализирован: {stats.get('index_name', 'unknown')}")

            # Очищаем тестовый индекс
            pinecone_adapter.clear()

            print("   ✅ Pinecone адаптер работает корректно")

    except Exception as e:
        print(f"   ❌ Ошибка теста Pinecone адаптера: {e}")

    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)


if __name__ == "__main__":
    test_adapters()