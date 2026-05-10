"""
Управление FAISS индексом для векторного поиска.
"""

import faiss
import numpy as np
import pickle
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class FAISSManager:
    """Класс для работы с FAISS индексом"""

    def __init__(self, index_path: str = None, metadata_path: str = None):
        """
        Инициализация менеджера FAISS.

        Args:
            index_path: Путь к файлу индекса
            metadata_path: Путь к файлу метаданных
        """
        self.index_path = Path(index_path) if index_path else Path("outputs/faiss_index.bin")
        self.metadata_path = Path(metadata_path) if metadata_path else Path("outputs/metadata.pkl")

        # Создаем директории если не существуют
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)

        self.index = None
        self.metadata = []
        self.dimension = None

    def create_index(self, dimension: int):
        """
        Создание нового FAISS индекса.

        Args:
            dimension: Размерность векторов
        """
        self.dimension = dimension
        # Используем L2 расстояние (евклидово расстояние)
        self.index = faiss.IndexFlatL2(dimension)
        self.metadata = []

        logger.info(f"Создан FAISS индекс с размерностью {dimension}")

    def add_to_index(self, vectors: np.ndarray, metadata: List[Dict[str, Any]]):
        """
        Добавление векторов в индекс.

        Args:
            vectors: Массив векторов
            metadata: Метаданные для каждого вектора
        """
        if self.index is None:
            raise ValueError("Индекс не создан. Сначала вызовите create_index()")

        if len(vectors) != len(metadata):
            raise ValueError("Количество векторов и метаданных должно совпадать")

        # Проверяем размерность
        if vectors.shape[1] != self.dimension:
            raise ValueError(
                f"Размерность векторов ({vectors.shape[1]}) не совпадает с размерностью индекса ({self.dimension})")

        # Добавляем векторы в индекс
        self.index.add(vectors.astype('float32'))

        # Добавляем метаданные
        self.metadata.extend(metadata)

        logger.info(f"Добавлено {len(vectors)} векторов. Всего: {self.index.ntotal}")

    def search(self, query_vector: np.ndarray, k: int = 5) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Поиск k ближайших соседей.

        Args:
            query_vector: Вектор запроса
            k: Количество ближайших соседей

        Returns:
            Tuple: (расстояния, метаданные найденных векторов)
        """
        if self.index is None or self.index.ntotal == 0:
            logger.warning("Индекс пуст или не создан")
            return np.array([]), []

        # Подготавливаем вектор запроса
        query_vector = query_vector.reshape(1, -1).astype('float32')

        # Выполняем поиск
        distances, indices = self.index.search(query_vector, k)

        # Получаем метаданные найденных векторов
        results = []
        valid_distances = []

        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.metadata):
                results.append(self.metadata[idx])
                valid_distances.append(distances[0][i])

        return np.array(valid_distances), results

    def save(self):
        """Сохранение индекса и метаданных на диск"""
        if self.index is None:
            logger.warning("Нет данных для сохранения")
            return

        # Сохраняем FAISS индекс
        faiss.write_index(self.index, str(self.index_path))

        # Сохраняем метаданные
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f)

        # Сохраняем конфигурацию
        config = {
            'dimension': self.dimension,
            'total_vectors': self.index.ntotal,
            'index_type': 'IndexFlatL2',
            'index_path': str(self.index_path),
            'metadata_path': str(self.metadata_path)
        }

        config_path = self.index_path.parent / "config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

        logger.info(f"Индекс сохранен: {self.index_path}")
        logger.info(f"Метаданные сохранены: {self.metadata_path}")
        logger.info(f"Всего векторов: {self.index.ntotal}")

    def load(self) -> bool:
        """
        Загрузка индекса и метаданных с диска.

        Returns:
            bool: Успешно ли загружено
        """
        try:
            # Проверяем существование файлов
            if not self.index_path.exists():
                logger.error(f"Файл индекса не найден: {self.index_path}")
                return False

            if not self.metadata_path.exists():
                logger.error(f"Файл метаданных не найден: {self.metadata_path}")
                return False

            # Загружаем FAISS индекс
            self.index = faiss.read_index(str(self.index_path))

            # Загружаем метаданные
            with open(self.metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)

            self.dimension = self.index.d

            logger.info(f"Индекс загружен: {self.index_path}")
            logger.info(f"Всего векторов: {self.index.ntotal}")
            logger.info(f"Размерность: {self.dimension}")

            return True

        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Получение статистики индекса.

        Returns:
            Dict: Статистика индекса
        """
        if self.index is None:
            return {"status": "Индекс не создан"}

        return {
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "metadata_count": len(self.metadata),
            "index_type": "IndexFlatL2",
            "index_path": str(self.index_path),
            "metadata_path": str(self.metadata_path)
        }

    def clear(self):
        """Очистка индекса и метаданных"""
        self.index = None
        self.metadata = []
        self.dimension = None
        logger.info("Индекс и метаданные очищены")


# Создаем глобальный экземпляр для удобства
faiss_manager = FAISSManager()