"""
Генератор эмбеддингов для текстов.
Использует предобученные модели для создания векторных представлений.
"""

import numpy as np
from typing import List, Optional, Union
import logging
from dataclasses import dataclass
from pathlib import Path
import time

# Импортируем настройки
try:
    from config import Config

    config = Config()
except ImportError:
    # Запасные настройки на случай ошибки импорта
    @dataclass
    class LocalConfig:
        EMBEDDING_MODEL = "cointegrated/LaBSE-en-ru"
        EMBEDDING_DIM = 768
        DEVICE = "cpu"
        BATCH_SIZE = 32


    config = LocalConfig()

# Настройка логирования
logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Класс для генерации эмбеддингов текстов.
    Поддерживает различные модели трансформеров.
    """

    def __init__(self,
                 model_name: Optional[str] = "cointegrated/LaBSE-en-ru",
                 device: Optional[str] = "cpu",
                 cache_dir: Optional[str] = None):
        """
        Инициализация генератора эмбеддингов.

        Args:
            model_name: Название модели (по умолчанию из config)
            device: Устройство для вычислений ('cpu' или 'cuda')
            cache_dir: Директория для кэширования модели
        """
        self.model_name = model_name or config.EMBEDDING_MODEL
        self.device = device or config.DEVICE
        self.cache_dir = cache_dir

        # Проверка доступности GPU
        self._check_device_availability()

        # Инициализация модели
        self.model = None
        self.tokenizer = None
        self._dimension = 768  # Размерность LaBSE модели

        # Метрики производительности
        self.stats = {
            'total_texts_processed': 0,
            'total_time_spent': 0.0,
            'avg_time_per_text': 0.0,
            'model_load_time': 0.0
        }

        # Загружаем модель
        self._load_model()

    def _check_device_availability(self):
        """Проверка доступности вычислительных устройств"""
        if self.device == 'cuda':
            try:
                import torch
                if not torch.cuda.is_available():
                    logger.warning("CUDA запрошена, но не доступна. Переключаюсь на CPU.")
                    self.device = 'cpu'
                else:
                    logger.info(f"Используется GPU: {torch.cuda.get_device_name(0)}")
            except ImportError:
                logger.warning("PyTorch не установлен. Использую CPU.")
                self.device = 'cpu'

    def _load_model(self):
        """Загрузка модели эмбеддингов"""
        start_time = time.time()

        try:
            # Пробуем загрузить Sentence Transformers
            logger.info(f"Загрузка модели: {self.model_name}")

            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(
                self.model_name,
                device=self.device,
                cache_folder=self.cache_dir
            )

            # Определяем размерность модели
            test_embedding = self.model.encode(["тест"])
            self._dimension = test_embedding.shape[1]

            load_time = time.time() - start_time
            self.stats['model_load_time'] = load_time

            logger.info(f"Модель загружена за {load_time:.2f} секунд")
            logger.info(f"Размерность эмбеддингов: {self._dimension}")
            logger.info(f"Устройство: {self.device}")

        except ImportError as e:
            logger.error(f"Не удалось импортировать SentenceTransformers: {e}")
            logger.info("Пробую альтернативный метод загрузки...")
            self._load_model_fallback()

    def _load_model_fallback(self):
        """Альтернативный метод загрузки модели"""
        try:
            logger.info("Использую альтернативный метод загрузки...")

            # Используем transformers напрямую
            from transformers import AutoModel, AutoTokenizer
            import torch

            start_time = time.time()

            # Загружаем токенизатор и модель
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)

            # Перемещаем модель на нужное устройство
            self.model = self.model.to(self.device)
            self.model.eval()  # Режим оценки

            # Определяем размерность
            with torch.no_grad():
                inputs = self.tokenizer("тест", return_tensors="pt", padding=True, truncation=True)
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                outputs = self.model(**inputs)
                # Берем эмбеддинги [CLS] токена
                self._dimension = outputs.last_hidden_state[:, 0, :].shape[1]

            load_time = time.time() - start_time
            self.stats['model_load_time'] = load_time

            logger.info(f"Модель загружена (fallback) за {load_time:.2f} секунд")
            logger.info(f"Размерность: {self._dimension}")

        except Exception as e:
            logger.error(f"Не удалось загрузить модель: {e}")
            raise RuntimeError(f"Не удалось загрузить модель {self.model_name}")

    def generate_embeddings(self,
                            texts: List[str],
                            batch_size: int = 32,
                            normalize: bool = True,
                            show_progress: bool = True) -> np.ndarray:
        """
        Генерация эмбеддингов для списка текстов.

        Args:
            texts: Список текстов для обработки
            batch_size: Размер батча для обработки
            normalize: Нормализовать векторы (рекомендуется для косинусного сходства)
            show_progress: Показывать прогресс-бар

        Returns:
            np.ndarray: Матрица эмбеддингов [n_texts x dimension]
        """
        if not texts:
            logger.warning("Передан пустой список текстов")
            return np.array([])

        logger.info(f"Генерация эмбеддингов для {len(texts)} текстов...")
        start_time = time.time()

        try:
            # Используем Sentence Transformers если доступен
            if hasattr(self, 'model') and not hasattr(self.model, 'encode'):
                # Используем fallback метод
                embeddings = self._generate_embeddings_fallback(texts, batch_size, normalize, show_progress)
            else:
                # Используем стандартный метод Sentence Transformers
                embeddings = self.model.encode(
                    texts,
                    batch_size=batch_size,
                    show_progress_bar=show_progress,
                    normalize_embeddings=normalize,
                    convert_to_numpy=True
                )

            # Обновляем статистику
            processing_time = time.time() - start_time
            self.stats['total_texts_processed'] += len(texts)
            self.stats['total_time_spent'] += processing_time
            self.stats['avg_time_per_text'] = (
                self.stats['total_time_spent'] / self.stats['total_texts_processed']
                if self.stats['total_texts_processed'] > 0 else 0
            )

            logger.info(f"Эмбеддинги созданы за {processing_time:.2f} секунд")
            logger.info(f"Размерность: {embeddings.shape}")

            return embeddings

        except Exception as e:
            logger.error(f"Ошибка генерации эмбеддингов: {e}")
            # Пробуем fallback метод
            logger.info("Пробую использовать fallback метод...")
            return self._generate_embeddings_fallback(texts, batch_size, normalize, show_progress)

    def _generate_embeddings_fallback(self,
                                      texts: List[str],
                                      batch_size: int,
                                      normalize: bool,
                                      show_progress: bool) -> np.ndarray:
        """Альтернативный метод генерации эмбеддингов"""
        import torch
        from tqdm import tqdm

        all_embeddings = []

        # Создаем прогресс-бар если нужно
        if show_progress:
            progress_bar = tqdm(total=len(texts), desc="Генерация эмбеддингов")

        # Обрабатываем батчами
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            # Токенизация
            inputs = self.tokenizer(
                batch_texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )

            # Перемещаем на нужное устройство
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Генерация эмбеддингов
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Используем эмбеддинги [CLS] токена
                batch_embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()

            # Нормализация если нужно
            if normalize:
                norms = np.linalg.norm(batch_embeddings, axis=1, keepdims=True)
                batch_embeddings = batch_embeddings / norms

            all_embeddings.append(batch_embeddings)

            if show_progress:
                progress_bar.update(len(batch_texts))

        if show_progress:
            progress_bar.close()

        # Объединяем все эмбеддинги
        return np.vstack(all_embeddings)

    def generate_single_embedding(self, text: str, normalize: bool = True) -> np.ndarray:
        """
        Генерация эмбеддинга для одного текста.

        Args:
            text: Текст для обработки
            normalize: Нормализовать вектор

        Returns:
            np.ndarray: Вектор эмбеддинга [dimension]
        """
        embeddings = self.generate_embeddings([text], normalize=normalize, show_progress=False)
        return embeddings[0] if len(embeddings) > 0 else np.array([])

    def get_embedding_dimension(self) -> int:
        """
        Получение размерности эмбеддингов.

        Returns:
            int: Размерность векторов
        """
        if self._dimension is None:
            # Определяем размерность через тестовый вызов
            test_embedding = self.generate_single_embedding("тест")
            self._dimension = test_embedding.shape[0]

        return self._dimension

    def get_model_info(self) -> dict:
        """
        Получение информации о модели.

        Returns:
            dict: Информация о модели и статистике использования
        """
        info = {
            'model_name': self.model_name,
            'embedding_dimension': self.get_embedding_dimension(),
            'device': self.device,
            'cache_dir': str(self.cache_dir) if self.cache_dir else None,
            'stats': self.stats.copy(),
            'is_sentence_transformers': hasattr(self.model, 'encode'),
            'has_tokenizer': self.tokenizer is not None
        }

        # Добавляем информацию о памяти GPU если используется
        if self.device == 'cuda':
            try:
                import torch
                info['gpu_memory_allocated'] = torch.cuda.memory_allocated() / 1024 ** 3  # в GB
                info['gpu_memory_cached'] = torch.cuda.memory_reserved() / 1024 ** 3  # в GB
            except:
                info['gpu_memory_info'] = 'не доступна'

        return info

    def save_embeddings(self,
                        embeddings: np.ndarray,
                        filepath: Union[str, Path],
                        metadata: Optional[List[dict]] = None):
        """
        Сохранение эмбеддингов в файл.

        Args:
            embeddings: Матрица эмбеддингов
            filepath: Путь для сохранения
            metadata: Метаданные для каждого эмбеддинга
        """
        import pickle

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'embeddings': embeddings,
            'model_name': self.model_name,
            'embedding_dimension': self._dimension,
            'timestamp': time.time()
        }

        if metadata is not None:
            data['metadata'] = metadata

        with open(filepath, 'wb') as f:
            pickle.dump(data, f)

        logger.info(f"Эмбеддинги сохранены в {filepath}")
        logger.info(f"Сохранено {len(embeddings)} векторов")

    def load_embeddings(self, filepath: Union[str, Path]) -> tuple:
        """
        Загрузка эмбеддингов из файла.

        Args:
            filepath: Путь к файлу с эмбеддингами

        Returns:
            tuple: (embeddings, metadata) или (embeddings, None)
        """
        import pickle

        with open(filepath, 'rb') as f:
            data = pickle.load(f)

        embeddings = data['embeddings']
        metadata = data.get('metadata', None)

        logger.info(f"Загружено {len(embeddings)} эмбеддингов из {filepath}")

        return embeddings, metadata

    def test_model(self, test_texts: Optional[List[str]] = None) -> dict:
        """
        Тестирование модели на наборе тестовых текстов.

        Args:
            test_texts: Список тестовых текстов

        Returns:
            dict: Результаты тестирования
        """
        if test_texts is None:
            test_texts = [
                "Привет, как дела?",
                "Расписание занятий на понедельник",
                "Где находится деканат?",
                "Как получить справку об обучении?",
                "Какие документы нужны для академотпуска?"
            ]

        logger.info(f"Тестирование модели на {len(test_texts)} текстах...")

        results = {
            'test_texts': test_texts,
            'embeddings_generated': False,
            'similarity_test': {}
        }

        try:
            # Генерация эмбеддингов
            start_time = time.time()
            embeddings = self.generate_embeddings(test_texts, show_progress=False)
            gen_time = time.time() - start_time

            results['embeddings_generated'] = True
            results['generation_time'] = gen_time
            results['embeddings_shape'] = embeddings.shape

            # Тест косинусного сходства
            from sklearn.metrics.pairwise import cosine_similarity

            # Проверяем, что похожие запросы имеют высокое сходство
            similar_pairs = [
                (0, 0),  # Тот же текст
                (1, 1),  # Тот же текст
                (2, 2),  # Тот же текст
            ]

            for i, j in similar_pairs:
                sim = cosine_similarity(
                    embeddings[i].reshape(1, -1),
                    embeddings[j].reshape(1, -1)
                )[0][0]
                results['similarity_test'][f'text_{i}_vs_{j}'] = {
                    'similarity': float(sim),
                    'expected_high': True
                }

            # Проверяем, что разные запросы имеют разумное сходство
            different_pairs = [
                (0, 1),  # Приветствие vs расписание
                (2, 3),  # Деканат vs справка
                (1, 4),  # Расписание vs академотпуск
            ]

            for i, j in different_pairs:
                sim = cosine_similarity(
                    embeddings[i].reshape(1, -1),
                    embeddings[j].reshape(1, -1)
                )[0][0]
                results['similarity_test'][f'text_{i}_vs_{j}'] = {
                    'similarity': float(sim),
                    'expected_high': False
                }

            logger.info("Тестирование завершено успешно")

        except Exception as e:
            logger.error(f"Ошибка при тестировании модели: {e}")
            results['error'] = str(e)

        return results


# Создание глобального экземпляра для удобства использования
try:
    # Инициализируем с настройками из конфига
    embedder = EmbeddingGenerator(
        model_name=config.EMBEDDING_MODEL,
        device=config.DEVICE
    )

    logger.info(f"Генератор эмбеддингов инициализирован с моделью: {config.EMBEDDING_MODEL}")

except Exception as e:
    logger.error(f"Не удалось инициализировать генератор эмбеддингов: {e}")
    embedder = None


# Тестовая функция для проверки работы
def test_embedding_generator():
    """Тестовая функция для проверки работы генератора"""
    print("=" * 60)
    print("ТЕСТ ГЕНЕРАТОРА ЭМБЕДДИНГОВ")
    print("=" * 60)

    if embedder is None:
        print("❌ Генератор не инициализирован")
        return

    # Получаем информацию о модели
    info = embedder.get_model_info()
    print(f"\n📋 ИНФОРМАЦИЯ О МОДЕЛИ:")
    print(f"   Модель: {info['model_name']}")
    print(f"   Размерность: {info['embedding_dimension']}")
    print(f"   Устройство: {info['device']}")

    # Тестовые тексты
    test_texts = [
        "Расписание занятий на завтра",
        "Где найти старосту группы?",
        "Как получить пропуск в общежитие?",
        "Когда начинается сессия?",
        "Контакты учебного отдела"
    ]

    print(f"\n🧪 ТЕСТИРОВАНИЕ НА {len(test_texts)} ТЕКСТАХ...")

    # Генерация эмбеддингов
    try:
        embeddings = embedder.generate_embeddings(test_texts, show_progress=True)

        print(f"\n✅ ЭМБЕДДИНГИ УСПЕШНО СОЗДАНЫ:")
        print(f"   Количество: {len(embeddings)}")
        print(f"   Размерность каждого: {embeddings.shape[1]}")
        print(f"   Общая форма: {embeddings.shape}")

        # Простой тест на сходство
        from sklearn.metrics.pairwise import cosine_similarity

        print(f"\n🔍 ТЕСТ КОСИНУСНОГО СХОДСТВА:")

        # Сравниваем первый текст с остальными
        for i in range(1, len(test_texts)):
            similarity = cosine_similarity(
                embeddings[0].reshape(1, -1),
                embeddings[i].reshape(1, -1)
            )[0][0]

            print(f"   '{test_texts[0][:30]}...' vs")
            print(f"   '{test_texts[i][:30]}...'")
            print(f"   Сходство: {similarity:.4f}")
            print()

        # Сохраняем тестовые эмбеддинги
        test_dir = Path("outputs/tests")
        test_dir.mkdir(exist_ok=True)

        embedder.save_embeddings(
            embeddings,
            test_dir / "test_embeddings.pkl",
            metadata=[{"text": t, "index": i} for i, t in enumerate(test_texts)]
        )

        print(f"\n💾 Тестовые эмбеддинги сохранены в outputs/tests/test_embeddings.pkl")

    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Запуск теста при прямом выполнении файла
    logging.basicConfig(level=logging.INFO)
    test_embedding_generator()