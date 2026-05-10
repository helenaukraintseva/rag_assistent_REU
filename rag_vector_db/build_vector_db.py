#!/usr/bin/env python3
"""
Упрощенная версия создания векторной базы данных.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List

import chromadb

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Добавляем путь для импорта
sys.path.insert(0, str(Path(__file__).parent))

try:
    from config import config
    from document_loader import DocumentLoader
    from text_splitter import TextSplitter

    # Проверяем наличие FAISS
    try:
        from chroma_manager import ChromaDBManager, get_embedding_function

        CHROMA_AVAILABLE = True
    except ImportError:
        logger.error("ChromaDB не установлен. Установите: pip install chromadb")
        CHROMA_AVAILABLE = False

    # Проверяем наличие sentence-transformers
    try:
        from sentence_transformers import SentenceTransformer

        ST_AVAILABLE = True
    except ImportError:
        logger.error("sentence-transformers не установлен. Установите: pip install sentence-transformers")
        ST_AVAILABLE = False

except ImportError as e:
    logger.error(f"Ошибка импорта: {e}")
    logger.error("Убедитесь что все файлы созданы:")
    logger.error("config.py, document_loader.py, text_splitter.py")
    sys.exit(1)


def create_test_documents():
    """Создание тестовых документов"""
    logger.info("Создание тестовых документов...")

    test_docs = [
        {
            'text': """
            Расписание занятий группы ПРО-42
            Понедельник: 9:00-10:30 Математика (ауд. 301)
            Вторник: 10:45-12:15 Программирование (ауд. 415)
            Среда: 14:00-15:30 Базы данных (ауд. 302)
            Контакты старосты: Иванов Иван, тел. 8-900-123-45-67
            """,
            'source': 'test_schedule.txt',
            'path': str(config.RAW_DATA_DIR / 'test_schedule.txt')
        },
        {
            'text': """
            Правила обучения в университете
            1. Посещение занятий обязательно
            2. Допускается пропуск не более 20% занятий
            3. Стипендия назначается при успешной сдаче сессии
            4. Академический отпуск предоставляется по медицинским показаниям
            """,
            'source': 'test_rules.txt',
            'path': str(config.RAW_DATA_DIR / 'test_rules.txt')
        }
    ]

    # Сохраняем тестовые документы
    for doc in test_docs:
        filepath = Path(doc['path'])
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(doc['text'].strip())
        logger.info(f"Создан файл: {filepath}")

    return test_docs


def main():
    """Основная функция"""
    logger.info("=" * 60)
    logger.info("СОЗДАНИЕ ВЕКТОРНОЙ БАЗЫ ДАННЫХ (ChromaDB)")
    logger.info("=" * 60)

    # Проверяем зависимости
    if not CHROMA_AVAILABLE or not ST_AVAILABLE:
        logger.error("Необходимые библиотеки не установлены")
        logger.info("Установите зависимости: pip install chromadb sentence-transformers")
        return False

    try:
        # 1. Загрузка документов
        logger.info("\n1. ЗАГРУЗКА ДОКУМЕНТОВ")
        loader = DocumentLoader()
        documents = loader.load_all_documents(str(config.RAW_DATA_DIR))

        # Если документов нет, создаем тестовые
        if not documents:
            logger.info("Документов не найдено. Создаю тестовые...")
            test_docs = create_test_documents()
            documents = test_docs
            # Перезагружаем документы из файлов
            documents = loader.load_all_documents(str(config.RAW_DATA_DIR))

        if not documents:
            logger.error("Не удалось загрузить документы")
            return False

        logger.info(f"Загружено документов: {len(documents)}")

        # 2. Разбиение на фрагменты
        logger.info("\n2. РАЗБИЕНИЕ НА ФРАГМЕНТЫ")
        splitter = TextSplitter()
        chunks = splitter.split_documents(
            documents,
            chunk_size=config.CHUNK_SIZE,
            overlap=config.CHUNK_OVERLAP
        )

        if not chunks:
            logger.error("Не удалось разбить документы на фрагменты")
            return False

        logger.info(f"Создано фрагментов: {len(chunks)}")

        # 3. Генерация эмбеддингов
        logger.info("\n3. ГЕНЕРАЦИЯ ЭМБЕДДИНГОВ")

        # Извлекаем тексты
        texts = [chunk['text'] for chunk in chunks]

        # Инициализируем модель
        logger.info(f"Загрузка модели: {config.EMBEDDING_MODEL}")
        model = SentenceTransformer(config.EMBEDDING_MODEL, device=config.DEVICE)

        # Генерируем эмбеддинги (для проверки)
        logger.info("Тестирование создания эмбеддингов...")
        test_embeddings = model.encode(
            texts[:min(5, len(texts))],
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True
        )

        logger.info(f"Тест эмбеддингов: размерность {test_embeddings.shape[1]}")

        # 4. Создание embedding function для ChromaDB
        logger.info("\n4. НАСТРОЙКА CHROMADB")

        # Создаем кастомную embedding function
        def chroma_embedding_function(texts: List[str]) -> List[List[float]]:
            """Функция для генерации эмбеддингов в ChromaDB"""
            embeddings = model.encode(
                texts,
                batch_size=32,
                show_progress_bar=False,
                normalize_embeddings=True
            )
            return embeddings.tolist()

        # 5. Инициализация и создание ChromaDB коллекции
        logger.info("\n5. СОЗДАНИЕ CHROMADB КОЛЛЕКЦИИ")

        chroma_manager = ChromaDBManager(
            persist_directory=str(config.OUTPUT_DIR / "chroma_db"),
            collection_name="documents",
            embedding_function=chroma_embedding_function
        )

        # Создаем коллекцию с метаданными
        collection_metadata = {
            "model": config.EMBEDDING_MODEL,
            "chunk_size": config.CHUNK_SIZE,
            "chunk_overlap": config.CHUNK_OVERLAP,
            "created_at": str(datetime.now()),
            "device": config.DEVICE,
            "embedding_dimension": test_embeddings.shape[1],
            "hnsw:space": "cosine"  # Используем косинусное расстояние
        }

        chroma_manager.create_collection(
            collection_name="documents",
            metadata=collection_metadata
        )

        # 6. Подготовка метаданных и добавление документов
        logger.info("\n6. ДОБАВЛЕНИЕ ДОКУМЕНТОВ В CHROMADB")

        # Подготавливаем метаданные для ChromaDB
        metadata_list = []
        for i, chunk in enumerate(chunks):
            metadata = {
                'source': chunk['metadata'].get('source', 'unknown'),
                'chunk_id': chunk['metadata'].get('chunk_id', 0),
                'total_chunks': chunk['metadata'].get('total_chunks', 1),
                'full_text_length': len(chunk['text']),
                'original_text': chunk['text'][:500] + "..." if len(chunk['text']) > 500 else chunk['text'],
                'file_path': chunk['metadata'].get('path', ''),
                'created_at': chunk['metadata'].get('created_at', str(datetime.now()))
            }
            metadata_list.append(metadata)

        # Добавляем документы батчами для экономии памяти
        batch_size = 100
        all_ids = []

        for i in range(0, len(texts), batch_size):
            end_idx = min(i + batch_size, len(texts))
            batch_texts = texts[i:end_idx]
            batch_metadata = metadata_list[i:end_idx]

            # Генерируем уникальные ID
            batch_ids = [f"doc_{j:06d}" for j in range(i, end_idx)]

            # Добавляем в ChromaDB
            added_ids = chroma_manager.add_documents(
                documents=batch_texts,
                metadatas=batch_metadata,
                ids=batch_ids
            )

            all_ids.extend(added_ids)
            logger.info(f"Добавлено {len(batch_texts)} документов (всего: {len(all_ids)})")

        # Сохраняем базу
        chroma_manager.save()

        # 7. Сохранение информации о сборке
        logger.info("\n7. СОХРАНЕНИЕ ИНФОРМАЦИИ О СБОРКЕ")

        build_info = {
            'timestamp': str(datetime.now()),
            'model': config.EMBEDDING_MODEL,
            'chunk_size': config.CHUNK_SIZE,
            'chunk_overlap': config.CHUNK_OVERLAP,
            'total_documents': len(documents),
            'total_chunks': len(chunks),
            'embedding_dimension': test_embeddings.shape[1],
            'vector_db': 'chromadb',
            'collection_name': 'documents',
            'persist_directory': str(config.OUTPUT_DIR / "chroma_db"),
            'device': config.DEVICE,
            'total_ids': len(all_ids),
            'chromadb_version': chromadb.__version__ if CHROMA_AVAILABLE else 'unknown'
        }

        info_path = config.OUTPUT_DIR / "build_info.json"
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(build_info, f, indent=2, ensure_ascii=False)

        # Сохраняем информацию о документах
        docs_info = {
            'documents': [
                {
                    'source': metadata['source'],
                    'chunk_id': metadata['chunk_id'],
                    'text_preview': metadata['original_text'],
                    'length': metadata['full_text_length']
                }
                for metadata in metadata_list[:100]  # Сохраняем первые 100 для примера
            ]
        }

        docs_info_path = config.OUTPUT_DIR / "documents_info.json"
        with open(docs_info_path, 'w', encoding='utf-8') as f:
            json.dump(docs_info, f, indent=2, ensure_ascii=False)

        # 8. Тестирование поиска
        logger.info("\n8. ТЕСТИРОВАНИЕ ПОИСКА")

        test_queries = [
            "расписание занятий",
            "контакты старосты",
            "правила обучения"
        ]

        for query in test_queries:
            results = chroma_manager.search([query], n_results=1)
            if results and results['documents']:
                logger.info(f"Тест поиска '{query}': найдено {len(results['documents'][0])} результатов")

        # 9. Вывод результатов
        logger.info("\n" + "=" * 60)
        logger.info("РЕЗУЛЬТАТЫ:")
        logger.info("=" * 60)
        logger.info(f"Документов обработано: {len(documents)}")
        logger.info(f"Фрагментов создано: {len(chunks)}")
        logger.info(f"Размерность эмбеддингов: {test_embeddings.shape[1]}")
        logger.info(f"ChromaDB коллекция: документы")
        logger.info(f"Persist directory: {config.OUTPUT_DIR / 'chroma_db'}")
        logger.info(f"Метаданные сохранены в коллекции")
        logger.info(f"Информация о сборке: {info_path}")

        # Получаем статистику коллекции
        collection_info = chroma_manager.get_collection_info()
        logger.info(f"Всего в коллекции: {collection_info.get('total_documents', 0)} документов")

        logger.info("\n✅ ВЕКТОРНАЯ БАЗА ДАННЫХ НА CHROMADB УСПЕШНО СОЗДАНА!")

        return True

    except Exception as e:
        logger.error(f"Ошибка при создании БД: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()

    if success:
        print("\n" + "=" * 60)
        print("🎉 УСПЕХ!")
        print("=" * 60)
        print(f"\nВекторная база данных создана в: {config.OUTPUT_DIR}")
        print("\nДля тестирования поиска:")
        print("1. Создайте файл search_demo.py")
        print("2. Или запустите интерактивный поиск:")
        print("   python -c \"import faiss; import pickle; print('FAISS работает!')\"")
        print("=" * 60)
    else:
        print("\n❌ ПРОИЗОШЛА ОШИБКА")
        sys.exit(1)