#!/usr/bin/env python3
"""
Модуль для поиска релевантных документов в векторной БД.
Подключается к ChromaDB и выполняет семантический поиск.
"""

import sys
import os
from pathlib import Path
import numpy as np
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import traceback

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Добавляем путь для импорта
sys.path.insert(0, str(Path(__file__).parent))

# Глобальный экземпляр ретривера
_retriever_instance = None
_retriever_cache = {}


@dataclass
class SearchResult:
    """Результат поиска"""
    text: str
    source: str
    score: float
    metadata: Dict[str, Any]
    distance: float = 0.0
    id: str = ""

    def __repr__(self):
        return f"SearchResult(source={self.source}, score={self.score:.4f}, id={self.id})"

    def to_dict(self):
        """Преобразование в словарь"""
        return {
            'text': self.text,
            'source': self.source,
            'score': float(self.score),
            'distance': float(self.distance),
            'id': self.id,
            'metadata': self.metadata
        }


class VectorDBRetriever:
    """
    Класс для поиска документов в векторной базе данных.
    Поддерживает ChromaDB и FAISS.
    """

    def __init__(self,
                 persist_directory: Optional[str] = None,
                 collection_name: Optional[str] = "documents",
                 embedding_model: Optional[str] = None,
                 use_chromadb: bool = True):
        """
        Инициализация ретривера.

        Args:
            persist_directory: Путь к директории с базой данных
            collection_name: Название коллекции (для ChromaDB)
            embedding_model: Название модели для эмбеддингов
            use_chromadb: Использовать ChromaDB (True) или FAISS (False)
        """
        self.use_chromadb = use_chromadb
        self.embedding_model_name = embedding_model
        self.embedder = None
        self.dimension = None

        # Статистика
        self.search_count = 0
        self.total_search_time = 0.0

        if collection_name is None:
            collection_name = "documents"
        self.collection_name = collection_name

        try:
            # Импортируем конфигурацию
            from config import config

            # Устанавливаем параметры по умолчанию из конфигурации
            if self.embedding_model_name is None:
                self.embedding_model_name = config.EMBEDDING_MODEL

            if self.use_chromadb:
                # ChromaDB конфигурация
                self.persist_directory = Path(
                    persist_directory) if persist_directory else config.OUTPUT_DIR / "chroma_db"
                self.collection_name = collection_name
                self.chroma_manager = None
                logger.info(f"Инициализация ChromaDB ретривера. Директория: {self.persist_directory}")
                self._initialize_chromadb()
            else:
                # FAISS конфигурация
                if persist_directory:
                    self.index_path = Path(persist_directory)
                else:
                    self.index_path = config.FAISS_INDEX_PATH if hasattr(config, 'FAISS_INDEX_PATH') else Path(
                        "outputs/faiss_index.bin")

                self.metadata_path = self.index_path.parent / "metadata.pkl"
                self.faiss_index = None
                self.metadata = []
                logger.info(f"Инициализация FAISS ретривера. Индекс: {self.index_path}")
                self._initialize_faiss()

            # Инициализируем модель эмбеддингов
            self._initialize_embedder()

            logger.info(
                f"Ретривер успешно инициализирован. Используется: {'ChromaDB' if self.use_chromadb else 'FAISS'}")

        except ImportError as e:
            logger.error(f"Ошибка импорта конфигурации: {e}")
            self._initialize_fallback()
        except Exception as e:
            logger.error(f"Ошибка инициализации ретривера: {e}")
            self._initialize_fallback()

    def _initialize_fallback(self):
        """Fallback инициализация для тестирования"""
        logger.warning("Использую fallback режим")
        self.dimension = 768
        self.embedder = None
        if self.use_chromadb:
            self.chroma_manager = None
        else:
            self.faiss_index = None
            self.metadata = []

    def _initialize_chromadb(self) -> bool:
        """Инициализация ChromaDB"""
        try:
            # Пытаемся импортировать необходимые модули
            try:
                from rag_vector_db.chroma_manager import ChromaDBManager
                chromadb_available = True
            except ImportError:
                logger.error("ChromaDBManager не найден")
                chromadb_available = False

            if not chromadb_available:
                return False

            # Создаем embedding function для ChromaDB с правильной сигнатурой
            embed_function = self._create_chromadb_embedding_function()

            if embed_function is None:
                logger.warning("Не удалось создать embedding function")

                # Создаем простую заглушку
                def simple_embed_function(input: List[str]) -> List[List[float]]:
                    import random
                    return [[random.random() for _ in range(384)] for _ in input]

                embed_function = simple_embed_function

            # ✅ ИСПРАВЛЕНО: Убеждаемся, что collection_name не None
            if self.collection_name is None:
                self.collection_name = "documents"
                logger.warning(f"collection_name был None, установлено значение по умолчанию: {self.collection_name}")

            # Инициализируем ChromaDB менеджер
            logger.info(f"Инициализация ChromaDBManager с collection_name='{self.collection_name}'")
            self.chroma_manager = ChromaDBManager(
                persist_directory=str(self.persist_directory),
                collection_name=self.collection_name,  # ✅ Теперь точно не None
                embedding_function=embed_function
            )

            # Пытаемся загрузить коллекцию
            try:
                logger.info(f"Попытка загрузки коллекции: {self.collection_name}")
                if not self.chroma_manager.load():
                    logger.warning(f"Коллекция {self.collection_name} не найдена, создаю новую...")
                    self.chroma_manager.create_collection()
            except Exception as e:
                logger.error(f"Ошибка загрузки коллекции ChromaDB: {e}")
                # Создаем новую коллекцию
                logger.info("Создание новой коллекции...")
                self.chroma_manager.create_collection()

            # Получаем информацию о коллекции
            try:
                info = self.chroma_manager.get_collection_info()
                self.dimension = 768  # Стандартная размерность
                logger.info(f"ChromaDB загружен. Документов: {info.get('total_documents', 0)}")
                return True
            except Exception as e:
                logger.error(f"Ошибка получения информации о коллекции: {e}")
                self.dimension = 768
                return True

        except Exception as e:
            logger.error(f"Критическая ошибка инициализации ChromaDB: {e}")
            logger.error(traceback.format_exc())
            return False

    def _create_chromadb_embedding_function(self):
        """Создание embedding function для ChromaDB с правильной сигнатурой"""
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(
                self.embedding_model_name,
                device='cpu'  # Используем CPU для простоты
            )

            # Правильная сигнатура для ChromaDB 0.4.16+
            def embed_function(input: List[str]) -> List[List[float]]:
                """Функция должна принимать один параметр 'input'"""
                embeddings = model.encode(
                    input,
                    batch_size=32,
                    show_progress_bar=False,
                    normalize_embeddings=True
                )
                return embeddings.tolist()

            return embed_function

        except ImportError:
            logger.error("SentenceTransformers не установлен")
            return None
        except Exception as e:
            logger.error(f"Ошибка создания embedding function: {e}")
            return None

    def _initialize_faiss(self) -> bool:
        """Инициализация FAISS"""
        try:
            # Пытаемся импортировать FAISS
            try:
                import faiss
                import pickle
                faiss_available = True
            except ImportError as e:
                logger.error(f"FAISS не установлен: {e}")
                return False

            if not self.index_path.exists():
                logger.error(f"Файл FAISS индекса не найден: {self.index_path}")
                # Создаем пустой индекс для тестирования
                self._create_fallback_faiss()
                return True

            logger.info(f"Загрузка FAISS индекса: {self.index_path}")

            # Загружаем индекс
            self.faiss_index = faiss.read_index(str(self.index_path))
            self.dimension = self.faiss_index.d

            # Загружаем метаданные
            if self.metadata_path.exists():
                with open(self.metadata_path, 'rb') as f:
                    self.metadata = pickle.load(f)
                logger.info(f"Загружено {len(self.metadata)} записей метаданных")
            else:
                self.metadata = []
                logger.warning(f"Файл метаданных не найден: {self.metadata_path}")

            logger.info(f"FAISS загружен. Векторов: {self.faiss_index.ntotal}, Размерность: {self.dimension}")
            return True

        except Exception as e:
            logger.error(f"Ошибка загрузки FAISS: {e}")
            logger.error(traceback.format_exc())
            self._create_fallback_faiss()
            return False

    def _create_fallback_faiss(self):
        """Создание fallback FAISS индекса для тестирования"""
        try:
            import faiss
            # Создаем пустой индекс
            self.dimension = 768
            self.faiss_index = faiss.IndexFlatL2(self.dimension)
            self.metadata = []
            logger.warning(f"Создан пустой FAISS индекс для тестирования")
        except ImportError:
            self.faiss_index = None
            self.metadata = []

    def _initialize_embedder(self):
        """Инициализация модели эмбеддингов для запросов"""
        try:
            # Пытаемся импортировать EmbeddingGenerator
            try:
                from embedding_generator import EmbeddingGenerator
                logger.info(f"Инициализация модели эмбеддингов: {self.embedding_model_name}")
                self.embedder = EmbeddingGenerator(
                    model_name=self.embedding_model_name,
                    device='cpu'  # Используем CPU для простоты
                )
                logger.info("Модель эмбеддингов инициализирована")
            except ImportError:
                logger.warning("EmbeddingGenerator не найден, использую fallback")
                self.embedder = None

        except Exception as e:
            logger.warning(f"Не удалось инициализировать модель эмбеддингов: {e}")
            self.embedder = None

    def search(self,
               query: str,
               k: int = 5,
               threshold: float = 0.0,
               where_filter: Optional[Dict] = None,
               return_scores: bool = True) -> List[SearchResult]:
        """
        Поиск релевантных документов по текстовому запросу.

        Args:
            query: Текст запроса
            k: Количество возвращаемых результатов
            threshold: Порог сходства (0-1, где 1 - максимальное сходство)
            where_filter: Фильтр по метаданным (только для ChromaDB)
            return_scores: Возвращать ли оценки сходства

        Returns:
            List[SearchResult]: Список найденных документов
        """
        self.search_count += 1
        search_start = datetime.now()

        logger.info(f"Поиск: '{query[:50]}...' (k={k}, threshold={threshold})")

        try:
            if self.use_chromadb:
                results = self._search_chromadb(query, k, threshold, where_filter)
            else:
                results = self._search_faiss(query, k, threshold)

            search_time = (datetime.now() - search_start).total_seconds()
            self.total_search_time += search_time

            logger.info(f"Найдено результатов: {len(results)} (за {search_time:.2f}с)")

            return results

        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            logger.error(traceback.format_exc())
            return []

    def _search_chromadb(self, query: str, k: int, threshold: float,
                         where_filter: Optional[Dict]) -> List[SearchResult]:
        """Поиск в ChromaDB"""
        if self.chroma_manager is None or self.chroma_manager.collection is None:
            logger.error("ChromaDB не инициализирован")
            return []

        try:
            # Выполняем поиск в ChromaDB
            results = self.chroma_manager.search(
                query_texts=[query],
                n_results=k * 2,  # Ищем больше, чтобы отфильтровать
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )

            # Обрабатываем результаты
            search_results = self._process_chromadb_results(results, query, threshold)

            # Сортируем по сходству и обрезаем
            search_results.sort(key=lambda x: x.score, reverse=True)
            search_results = search_results[:k]

            return search_results

        except Exception as e:
            logger.error(f"Ошибка поиска в ChromaDB: {e}")
            return []

    def _search_faiss(self, query: str, k: int, threshold: float) -> List[SearchResult]:
        """Поиск в FAISS"""
        if self.faiss_index is None:
            logger.error("FAISS индекс не загружен")
            return []

        try:
            # Генерируем эмбеддинг для запроса
            query_embedding = self._get_query_embedding(query)
            if query_embedding is None:
                logger.error("Не удалось создать эмбеддинг для запроса")
                return []

            # Подготавливаем вектор запроса
            query_vector = query_embedding.reshape(1, -1).astype('float32')

            # Ищем в FAISS
            k_search = min(k * 2, self.faiss_index.ntotal)  # Не запрашиваем больше чем есть
            distances, indices = self.faiss_index.search(query_vector, k_search)

            # Обрабатываем результаты
            search_results = []
            for distance, idx in zip(distances[0], indices[0]):
                if idx == -1 or idx >= len(self.metadata):
                    continue

                # Преобразуем расстояние в сходство
                score = self._distance_to_similarity(distance)

                if score < threshold:
                    continue

                metadata = self.metadata[idx] if idx < len(self.metadata) else {}
                search_results.append(SearchResult(
                    text=metadata.get('text', ''),
                    source=metadata.get('source', 'unknown'),
                    score=score,
                    distance=float(distance),
                    metadata=metadata,
                    id=f"faiss_{idx}"
                ))

            # Сортируем по сходству
            search_results.sort(key=lambda x: x.score, reverse=True)
            search_results = search_results[:k]

            return search_results

        except Exception as e:
            logger.error(f"Ошибка поиска в FAISS: {e}")
            return []

    def _process_chromadb_results(self, results: Dict, query: str, threshold: float) -> List[SearchResult]:
        """Обработка результатов поиска из ChromaDB"""
        search_results = []

        if not results or not results.get('documents'):
            return search_results

        documents = results['documents'][0]
        metadatas = results['metadatas'][0] if results.get('metadatas') else [{}] * len(documents)
        distances = results['distances'][0] if results.get('distances') else [0.0] * len(documents)
        ids = results['ids'][0] if results.get('ids') else [""] * len(documents)

        for i, (doc, metadata, distance, doc_id) in enumerate(zip(documents, metadatas, distances, ids)):
            if not doc or not doc.strip():
                continue

            # Преобразуем расстояние в сходство
            score = self._distance_to_similarity(distance)

            # Применяем порог
            if score < threshold:
                continue

            # Создаем объект результата
            result = SearchResult(
                text=doc,
                source=metadata.get('source', 'unknown'),
                score=score,
                distance=float(distance),
                metadata={
                    **metadata,
                    'original_query': query,
                    'result_index': i,
                    'chromadb_id': doc_id
                },
                id=doc_id
            )

            search_results.append(result)

        return search_results

    def _get_query_embedding(self, query: str) -> Optional[np.ndarray]:
        """Генерация эмбеддинга для текстового запроса (для FAISS)"""
        if self.embedder is not None:
            try:
                # Проверяем, есть ли у embedder нужный метод
                if hasattr(self.embedder, 'generate_single_embedding'):
                    embedding = self.embedder.generate_single_embedding(query)
                elif hasattr(self.embedder, 'generate_embeddings'):
                    embeddings = self.embedder.generate_embeddings([query])
                    embedding = embeddings[0]
                else:
                    embedding = None

                if embedding is not None:
                    return embedding.astype('float32')
            except Exception as e:
                logger.warning(f"Ошибка генерации эмбеддинга: {e}")

        # Fallback для демонстрации
        if self.dimension:
            return np.random.randn(self.dimension).astype('float32')

        return None

    def _distance_to_similarity(self, distance: float) -> float:
        """
        Преобразование расстояния в оценку сходства (0-1).
        """
        if self.use_chromadb:
            # ChromaDB использует косинусное расстояние (0-2, где 0 - идентичные)
            similarity = 1.0 - (distance / 2.0)
        else:
            # FAISS L2 расстояние - преобразуем в сходство
            similarity = 1.0 / (1.0 + distance)

        # Ограничиваем диапазон 0-1
        return max(0.0, min(1.0, similarity))

    def get_index_stats(self) -> Dict[str, Any]:
        """Получение статистики индекса"""
        stats = {
            "embedding_model": self.embedding_model_name,
            "search_count": self.search_count,
            "vector_db": "chromadb" if self.use_chromadb else "faiss"
        }

        if self.search_count > 0:
            stats["avg_search_time"] = self.total_search_time / self.search_count

        if self.use_chromadb:
            if self.chroma_manager is None:
                stats["status"] = "ChromaDB не инициализирован"
                return stats

            try:
                info = self.chroma_manager.get_collection_info()
                stats.update({
                    "total_documents": info.get('total_documents', 0),
                    "collection_name": self.collection_name,
                    "persist_directory": str(self.persist_directory)
                })
            except Exception as e:
                stats["error"] = str(e)
        else:
            if self.faiss_index is None:
                stats["status"] = "FAISS индекс не загружен"
                return stats

            stats.update({
                "total_vectors": self.faiss_index.ntotal if hasattr(self.faiss_index, 'ntotal') else 0,
                "dimension": self.dimension,
                "metadata_count": len(self.metadata),
                "index_path": str(self.index_path) if hasattr(self, 'index_path') else "unknown"
            })

        return stats

    def health_check(self) -> Dict[str, Any]:
        """Проверка работоспособности ретривера"""
        health = {
            "vector_db": "chromadb" if self.use_chromadb else "faiss",
            "embedder_initialized": self.embedder is not None,
            "dimension": self.dimension
        }

        if self.use_chromadb:
            health["chromadb_loaded"] = self.chroma_manager is not None
            health["collection_loaded"] = self.chroma_manager is not None and self.chroma_manager.collection is not None

            if health["collection_loaded"]:
                try:
                    info = self.chroma_manager.get_collection_info()
                    health["total_documents"] = info.get('total_documents', 0)
                except Exception as e:
                    health["collection_error"] = str(e)
        else:
            health["faiss_loaded"] = self.faiss_index is not None
            health["metadata_loaded"] = len(self.metadata) > 0

            if health["faiss_loaded"]:
                health["total_vectors"] = self.faiss_index.ntotal if hasattr(self.faiss_index, 'ntotal') else 0

        # Тестовый поиск
        try:
            test_results = self.search("тест", k=1, threshold=0.0)
            health["test_search"] = True
            health["test_results_count"] = len(test_results)
        except Exception as e:
            health["test_search"] = False
            health["test_error"] = str(e)

        return health


def get_retriever(persist_directory: Optional[str] = None,
                  collection_name: Optional[str] = "documents",
                  embedding_model: Optional[str] = None,
                  use_chromadb: bool = True,
                  force_new: bool = False) -> VectorDBRetriever:
    """
    Фабричная функция для получения экземпляра ретривера.
    Поддерживает кэширование и создание новых экземпляров.

    Args:
        persist_directory: Путь к директории с базой данных
        collection_name: Название коллекции (для ChromaDB)
        embedding_model: Название модели для эмбеддингов
        use_chromadb: Использовать ChromaDB (True) или FAISS (False)
        force_new: Принудительно создать новый экземпляр

    Returns:
        VectorDBRetriever: Экземпляр ретривера
    """
    global _retriever_instance, _retriever_cache

    if collection_name is None:
        collection_name = "documents"

    # Создаем ключ для кэша
    cache_key = f"{persist_directory}:{collection_name}:{embedding_model}:{use_chromadb}"

    # Проверяем, нужно ли использовать кэш
    if not force_new and cache_key in _retriever_cache:
        logger.debug(f"Используется кэшированный ретривер для ключа: {cache_key}")
        return _retriever_cache[cache_key]

    try:
        logger.info(f"Создание нового ретривера: use_chromadb={use_chromadb}")

        retriever = VectorDBRetriever(
            persist_directory=persist_directory,
            collection_name=collection_name,
            embedding_model=embedding_model,
            use_chromadb=use_chromadb
        )

        # Сохраняем в кэш
        _retriever_cache[cache_key] = retriever

        # Для обратной совместимости сохраняем как глобальный экземпляр
        _retriever_instance = retriever

        return retriever

    except Exception as e:
        logger.error(f"Ошибка создания ретривера: {e}")
        logger.error(traceback.format_exc())
        raise RuntimeError(f"Не удалось создать ретривер: {str(e)}")


def search_query(query: str, k: int = 5, **kwargs) -> List[Dict[str, Any]]:
    """
    Упрощенная функция для поиска одного запроса.

    Args:
        query: Текст запроса
        k: Количество результатов
        **kwargs: Дополнительные параметры для ретривера

    Returns:
        List[Dict]: Результаты поиска в виде словарей
    """
    try:
        retriever = get_retriever(**kwargs)
        results = retriever.search(query, k=k)
        return [r.to_dict() for r in results]
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        return []


def main():
    """Демонстрация работы ретривера"""
    print("=" * 60)
    print("ДЕМОНСТРАЦИЯ РЕТРИВЕРА ВЕКТОРНОЙ БД")
    print("=" * 60)

    try:
        # Пытаемся загрузить конфигурацию для получения путей
        try:
            from config import config
            default_persist_dir = str(config.OUTPUT_DIR / "chroma_db")
            print(f"Конфигурация загружена. Путь по умолчанию: {default_persist_dir}")
        except ImportError:
            default_persist_dir = "outputs/chroma_db"
            print(f"Конфигурация не найдена, использую путь по умолчанию: {default_persist_dir}")

        # Пытаемся использовать ChromaDB
        print("\n1. ПРОВЕРКА CHROMADB:")
        try:
            retriever_chroma = get_retriever(
                persist_directory=default_persist_dir,
                use_chromadb=True,
                force_new=True
            )
            health_chroma = retriever_chroma.health_check()

            for key, value in health_chroma.items():
                status = "✅" if (value is True or (isinstance(value, (int, float)) and value > 0)) else "❌"
                print(f"   {status} {key}: {value}")

            if health_chroma.get("chromadb_loaded", False):
                print("   ChromaDB загружен успешно!")
            else:
                print("   ChromaDB не загружен, проверяем FAISS...")

        except Exception as e:
            print(f"   ❌ Ошибка ChromaDB: {e}")

        # Пытаемся использовать FAISS
        print("\n2. ПРОВЕРКА FAISS:")
        try:
            faiss_path = "outputs/faiss_index.bin"
            retriever_faiss = get_retriever(
                persist_directory=faiss_path,
                use_chromadb=False,
                force_new=True
            )
            health_faiss = retriever_faiss.health_check()

            for key, value in health_faiss.items():
                status = "✅" if (value is True or (isinstance(value, (int, float)) and value > 0)) else "❌"
                print(f"   {status} {key}: {value}")

            if health_faiss.get("faiss_loaded", False):
                print("   FAISS загружен успешно!")
                retriever = retriever_faiss  # Используем FAISS как основной
            else:
                print("   FAISS не загружен")
                retriever = retriever_chroma  # Используем ChromaDB как fallback

        except Exception as e:
            print(f"   ❌ Ошибка FAISS: {e}")
            retriever = retriever_chroma  # Используем ChromaDB

        # Показываем статистику
        print("\n3. СТАТИСТИКА:")
        stats = retriever.get_index_stats()
        for key, value in stats.items():
            if key not in ["index_path", "persist_directory"]:
                print(f"   {key}: {value}")

        # Примеры поиска
        print("\n4. ПРИМЕРЫ ПОИСКА:")

        test_queries = [
            "расписание занятий",
            "контакты деканата",
            "правила обучения",
            "стипендия",
            "академический отпуск"
        ]

        for query in test_queries:
            print(f"\n🔍 Поиск: '{query}'")
            results = retriever.search(query, k=2)

            if not results:
                print("   ❌ Ничего не найдено")
                continue

            for i, result in enumerate(results, 1):
                print(f"   {i}. [{result.source}] (сходство: {result.score:.3f})")
                preview = result.text[:80].replace('\n', ' ')
                print(f"      {preview}...")

        # Интерактивный поиск
        print("\n" + "=" * 60)
        print("ИНТЕРАКТИВНЫЙ ПОИСК")
        print("=" * 60)
        print("Введите запросы для поиска (или 'выход' для завершения)")

        while True:
            try:
                query = input("\n📝 Ваш запрос: ").strip()

                if query.lower() in ['выход', 'exit', 'quit', '']:
                    break

                if not query:
                    continue

                print(f"\n🔎 Поиск: '{query}'")

                # Выполняем поиск
                results = retriever.search(query, k=3)

                if not results:
                    print("   ❌ Ничего не найдено")
                    continue

                # Выводим результаты
                for i, result in enumerate(results, 1):
                    print(f"\n   📄 РЕЗУЛЬТАТ {i}:")
                    print(f"      📁 Источник: {result.source}")
                    print(f"      ⭐ Сходство: {result.score:.4f}")
                    print(f"      📝 Текст:")

                    # Красиво форматируем текст
                    text = result.text
                    lines = text.split('\n')
                    for line in lines[:3]:  # Показываем первые 3 строки
                        if line.strip():
                            print(f"         {line[:100]}{'...' if len(line) > 100 else ''}")

                    if len(lines) > 3:
                        print(f"         ... и еще {len(lines) - 3} строк")

            except KeyboardInterrupt:
                print("\n\n👋 Завершение работы...")
                break
            except Exception as e:
                print(f"❌ Ошибка: {e}")

        print("\n" + "=" * 60)
        print("📊 ИТОГОВАЯ СТАТИСТИКА:")
        print("=" * 60)
        final_stats = retriever.get_index_stats()
        print(f"Всего выполнено поисков: {final_stats.get('search_count', 0)}")
        print(f"Всего документов в базе: {final_stats.get('total_documents', final_stats.get('total_vectors', 0))}")

    except Exception as e:
        print(f"\n❌ Ошибка инициализации ретривера: {e}")
        print(traceback.format_exc())
        print("\nУбедитесь что:")
        print("1. Для ChromaDB: запущен build_vector_db.py")
        print("2. Для FAISS: существуют файлы outputs/faiss_index.bin и outputs/metadata.pkl")
        print("3. Установлены зависимости: pip install chromadb sentence-transformers")


if __name__ == "__main__":
    main()