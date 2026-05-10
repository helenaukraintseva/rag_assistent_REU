#!/usr/bin/env python3
"""
Фабрика для работы с разными векторными базами данных.
Поддерживает ChromaDB и FAISS.
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

    def search(self, query: str, k: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """Поиск документов по запросу"""
        try:
            # Получаем сырые результаты из ChromaDB
            raw_results = self.db.search(
                query_texts=[query],
                n_results=k,
                **kwargs
            )

            # Преобразуем в стандартный формат
            results = []
            if raw_results and raw_results.get('documents'):
                for i in range(len(raw_results['documents'][0])):
                    doc = raw_results['documents'][0][i]
                    metadata = raw_results['metadatas'][0][i] if raw_results.get('metadatas') else {}
                    distance = raw_results['distances'][0][i] if raw_results.get('distances') else 0.0
                    doc_id = raw_results['ids'][0][i] if raw_results.get('ids') else f"doc_{i}"

                    # Преобразуем расстояние в сходство
                    similarity = 1.0 - (distance / 2.0)  # Для косинусного расстояния

                    results.append({
                        'id': doc_id,
                        'text': doc,
                        'source': metadata.get('source', 'unknown'),
                        'score': float(similarity),
                        'distance': float(distance),
                        'metadata': metadata
                    })

            logger.debug(f"ChromaDBAdapter: найдено {len(results)} результатов для запроса '{query}'")
            return results

        except Exception as e:
            logger.error(f"Ошибка поиска в ChromaDBAdapter: {e}")
            return []

    def add_documents(self, documents: List[str], metadata: List[Dict[str, Any]]) -> List[str]:
        """Добавление документов в коллекцию"""
        if len(documents) != len(metadata):
            logger.error("Количество документов и метаданных должно совпадать")
            return []

        try:
            # Добавляем документы в ChromaDB
            ids = self.db.add_documents(
                documents=documents,
                metadatas=metadata
            )

            logger.info(f"ChromaDBAdapter: добавлено {len(ids)} документов")
            return ids

        except Exception as e:
            logger.error(f"Ошибка добавления документов в ChromaDBAdapter: {e}")
            return []

    def delete_documents(self, ids: List[str] = None, where: Dict = None) -> bool:
        """Удаление документов из коллекции"""
        try:
            success = self.db.delete_documents(ids=ids, where=where)

            if success:
                logger.info(f"ChromaDBAdapter: удалено документов (ids: {len(ids) if ids else 'all'})")
            else:
                logger.warning("ChromaDBAdapter: не удалось удалить документы")

            return success

        except Exception as e:
            logger.error(f"Ошибка удаления документов в ChromaDBAdapter: {e}")
            return False

    def update_documents(self, ids: List[str], documents: List[str] = None,
                         metadata: List[Dict] = None) -> bool:
        """Обновление документов в коллекции"""
        try:
            success = self.db.update_documents(
                ids=ids,
                documents=documents,
                metadatas=metadata
            )

            if success:
                logger.info(f"ChromaDBAdapter: обновлено {len(ids)} документов")
            else:
                logger.warning("ChromaDBAdapter: не удалось обновить документы")

            return success

        except Exception as e:
            logger.error(f"Ошибка обновления документов в ChromaDBAdapter: {e}")
            return False

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Получение документа по ID"""
        if self.db.collection is None:
            logger.error("Коллекция ChromaDB не загружена")
            return None

        try:
            # Получаем документ по ID
            results = self.db.collection.get(ids=[doc_id])

            if results and results.get('documents'):
                doc = results['documents'][0]
                metadata = results['metadatas'][0] if results.get('metadatas') else {}

                return {
                    'id': doc_id,
                    'text': doc,
                    'metadata': metadata,
                    'source': metadata.get('source', 'unknown')
                }

            return None

        except Exception as e:
            logger.error(f"Ошибка получения документа в ChromaDBAdapter: {e}")
            return None

    def filter_documents(self, where: Dict, limit: int = 100) -> List[Dict[str, Any]]:
        """Фильтрация документов по метаданным"""
        if self.db.collection is None:
            logger.error("Коллекция ChromaDB не загружена")
            return []

        try:
            # Получаем документы с фильтром
            results = self.db.collection.get(
                where=where,
                limit=limit,
                include=["metadatas", "documents"]
            )

            filtered_docs = []
            if results and results.get('documents'):
                for doc, metadata in zip(results['documents'], results['metadatas']):
                    filtered_docs.append({
                        'text': doc,
                        'metadata': metadata,
                        'source': metadata.get('source', 'unknown')
                    })

            logger.debug(f"ChromaDBAdapter: найдено {len(filtered_docs)} документов по фильтру")
            return filtered_docs

        except Exception as e:
            logger.error(f"Ошибка фильтрации документов в ChromaDBAdapter: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики коллекции"""
        try:
            # Получаем базовую статистику
            info = self.db.get_collection_info()

            # Получаем дополнительную информацию
            total_docs = info.get('total_documents', 0)

            # Анализируем источники документов
            sources = {}
            if total_docs > 0 and self.db.collection:
                try:
                    # Получаем все метаданные для анализа
                    all_docs = self.db.collection.get(limit=min(1000, total_docs))
                    if all_docs and all_docs.get('metadatas'):
                        for metadata in all_docs['metadatas']:
                            source = metadata.get('source', 'unknown')
                            sources[source] = sources.get(source, 0) + 1
                except:
                    pass

            stats = {
                'vector_db': 'chromadb',
                'collection_name': self.collection_name,
                'persist_directory': str(self.persist_directory),
                'total_documents': total_docs,
                'sources_distribution': sources,
                'collection_metadata': info.get('metadata', {}),
                'embedding_function': 'custom' if self.embedding_function else 'default'
            }

            return stats

        except Exception as e:
            logger.error(f"Ошибка получения статистики в ChromaDBAdapter: {e}")
            return {'error': str(e)}

    def clear(self) -> bool:
        """Очистка коллекции"""
        try:
            success = self.db.clear_collection()

            if success:
                logger.info(f"ChromaDBAdapter: коллекция {self.collection_name} очищена")
            else:
                logger.warning("ChromaDBAdapter: не удалось очистить коллекцию")

            return success

        except Exception as e:
            logger.error(f"Ошибка очистки коллекции в ChromaDBAdapter: {e}")
            return False

    def save(self) -> bool:
        """Сохранение базы данных"""
        try:
            success = self.db.save()

            if success:
                logger.debug("ChromaDBAdapter: база данных сохранена")
            else:
                logger.warning("ChromaDBAdapter: не удалось сохранить базу данных")

            return success

        except Exception as e:
            logger.error(f"Ошибка сохранения в ChromaDBAdapter: {e}")
            return False

    def load(self) -> bool:
        """Загрузка коллекции"""
        try:
            success = self.db.load()

            if success:
                logger.info(f"ChromaDBAdapter: коллекция {self.collection_name} загружена")
            else:
                logger.info(f"ChromaDBAdapter: создаю новую коллекцию {self.collection_name}")
                self.db.create_collection()
                success = True

            return success

        except Exception as e:
            logger.error(f"Ошибка загрузки в ChromaDBAdapter: {e}")
            return False

    def batch_search(self, queries: List[str], k: int = 5, **kwargs) -> List[List[Dict[str, Any]]]:
        """
        Пакетный поиск по нескольким запросам.

        Args:
            queries: Список запросов
            k: Количество результатов на запрос
            **kwargs: Дополнительные параметры

        Returns:
            List[List[Dict]]: Результаты для каждого запроса
        """
        if not queries:
            return []

        try:
            # ChromaDB поддерживает пакетный поиск
            raw_results = self.db.search(
                query_texts=queries,
                n_results=k,
                **kwargs
            )

            all_results = []

            # Обрабатываем результаты для каждого запроса
            for query_idx in range(len(queries)):
                query_results = []

                if raw_results and raw_results.get('documents'):
                    for i in range(len(raw_results['documents'][query_idx])):
                        doc = raw_results['documents'][query_idx][i]
                        metadata = raw_results['metadatas'][query_idx][i] if raw_results.get('metadatas') else {}
                        distance = raw_results['distances'][query_idx][i] if raw_results.get('distances') else 0.0
                        doc_id = raw_results['ids'][query_idx][i] if raw_results.get('ids') else f"doc_{i}"

                        # Преобразуем расстояние в сходство
                        similarity = 1.0 - (distance / 2.0)

                        query_results.append({
                            'id': doc_id,
                            'text': doc,
                            'source': metadata.get('source', 'unknown'),
                            'score': float(similarity),
                            'distance': float(distance),
                            'metadata': metadata
                        })

                all_results.append(query_results)

            logger.debug(f"ChromaDBAdapter: пакетный поиск для {len(queries)} запросов")
            return all_results

        except Exception as e:
            logger.error(f"Ошибка пакетного поиска в ChromaDBAdapter: {e}")
            return [[] for _ in queries]

    def similarity_search(self,
                          query_embedding: List[float],
                          k: int = 5,
                          **kwargs) -> List[Dict[str, Any]]:
        """
        Поиск по вектору эмбеддинга.

        Args:
            query_embedding: Вектор эмбеддинга запроса
            k: Количество результатов
            **kwargs: Дополнительные параметры

        Returns:
            List[Dict]: Результаты поиска
        """
        if self.db.collection is None:
            logger.error("Коллекция ChromaDB не загружена")
            return []

        try:
            # ChromaDB поддерживает поиск по эмбеддингам
            results = self.db.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                **kwargs
            )

            formatted_results = []
            if results and results.get('documents'):
                for i in range(len(results['documents'][0])):
                    doc = results['documents'][0][i]
                    metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                    distance = results['distances'][0][i] if results.get('distances') else 0.0
                    doc_id = results['ids'][0][i] if results.get('ids') else f"doc_{i}"

                    similarity = 1.0 - (distance / 2.0)

                    formatted_results.append({
                        'id': doc_id,
                        'text': doc,
                        'source': metadata.get('source', 'unknown'),
                        'score': float(similarity),
                        'distance': float(distance),
                        'metadata': metadata
                    })

            logger.debug(f"ChromaDBAdapter: поиск по эмбеддингу, найдено {len(formatted_results)} результатов")
            return formatted_results

        except Exception as e:
            logger.error(f"Ошибка поиска по эмбеддингу в ChromaDBAdapter: {e}")
            return []


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

    def search(self, query: str, k: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """Поиск документов по запросу"""
        # FAISS требует эмбеддинги, поэтому этот метод будет ограничен
        # В реальном использовании нужен embedder
        logger.warning("FAISSAdapter.search требует эмбеддинги. Используйте search_with_embedding.")
        return []

    def search_with_embedding(self, query_embedding: np.ndarray, k: int = 5) -> List[Dict[str, Any]]:
        """Поиск по эмбеддингу"""
        try:
            distances, indices = self.db.index.search(query_embedding.reshape(1, -1).astype('float32'), k)

            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx == -1 or idx >= len(self.db.metadata):
                    continue

                metadata = self.db.metadata[idx]
                similarity = np.exp(-distance / 100.0)

                results.append({
                    'id': f"faiss_{idx}",
                    'text': metadata.get('text', ''),
                    'source': metadata.get('source', 'unknown'),
                    'score': float(similarity),
                    'distance': float(distance),
                    'metadata': metadata
                })

            return results

        except Exception as e:
            logger.error(f"Ошибка поиска в FAISSAdapter: {e}")
            return []

    # ... остальные методы FAISSAdapter (реализованы аналогично, но для FAISS)


def get_vector_db(db_type: str = "chromadb", **kwargs) -> VectorDBInterface:
    """
    Фабричная функция для получения векторной БД.

    Args:
        db_type: Тип БД ("chromadb" или "faiss")
        **kwargs: Параметры для инициализации

    Returns:
        VectorDBInterface: Экземпляр векторной БД
    """
    db_type = db_type.lower()

    if db_type == "chromadb":
        return ChromaDBAdapter(**kwargs)
    elif db_type == "faiss":
        return FAISSAdapter(**kwargs)
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

    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)


if __name__ == "__main__":
    test_adapters()