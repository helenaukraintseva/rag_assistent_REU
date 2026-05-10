"""
Демонстрация поиска в векторной базе данных.
"""

import sys
from pathlib import Path
import numpy as np
import pickle

# Добавляем путь для импорта
sys.path.insert(0, str(Path(__file__).parent))

from config import config


def test_search():
    """Тестирование поиска"""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ПОИСКА В ВЕКТОРНОЙ БД")
    print("=" * 60)

    # Проверяем наличие файлов
    if not config.FAISS_INDEX_PATH.exists():
        print(f"❌ Файл индекса не найден: {config.FAISS_INDEX_PATH}")
        print("Сначала запустите: python build_vector_db.py")
        return False

    if not config.METADATA_PATH.exists():
        print(f"❌ Файл метаданных не найден: {config.METADATA_PATH}")
        return False

    try:
        # Загружаем FAISS
        import faiss

        print("\n1. Загрузка FAISS индекса...")
        index = faiss.read_index(str(config.FAISS_INDEX_PATH))

        print(f"   Векторов в индексе: {index.ntotal}")
        print(f"   Размерность: {index.d}")

        # Загружаем метаданные
        print("\n2. Загрузка метаданных...")
        with open(config.METADATA_PATH, 'rb') as f:
            metadata = pickle.load(f)

        print(f"   Записей метаданных: {len(metadata)}")

        # Простой тестовый запрос
        print("\n3. Тестовый поиск...")

        # Создаем случайный вектор запроса (в реальности это будет эмбеддинг текста)
        query_vector = np.random.randn(1, index.d).astype('float32')

        # Ищем 3 ближайших соседа
        distances, indices = index.search(query_vector, k=3)

        print(f"\nРезультаты поиска:")
        print("-" * 40)

        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx != -1 and idx < len(metadata):
                result = metadata[idx]
                print(f"\nРезультат {i + 1}:")
                print(f"  Расстояние: {distance:.4f}")
                print(f"  Источник: {result.get('source', 'неизвестно')}")
                print(f"  Фрагмент {result.get('chunk_id', 0) + 1}/{result.get('total_chunks', 1)}")
                text_preview = result.get('text', '')[:100]
                print(f"  Текст: {text_preview}...")

        print("\n✅ Поиск работает корректно!")
        print("\n⚠️  Примечание: Это тест со случайным вектором.")
        print("   Для реального поиска нужна модель эмбеддингов.")

        return True

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_search()