#!/usr/bin/env python3
"""
Миграция данных из FAISS в ChromaDB.
"""

import pickle
import faiss
import numpy as np
from pathlib import Path
import json
from chroma_manager import ChromaDBManager, get_embedding_function


def migrate_faiss_to_chromadb(faiss_index_path: str,
                              metadata_path: str,
                              chroma_persist_dir: str = "chroma_db",
                              collection_name: str = "documents",
                              model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    """
    Миграция данных из FAISS в ChromaDB.

    Args:
        faiss_index_path: Путь к FAISS индексу
        metadata_path: Путь к метаданным
        chroma_persist_dir: Директория для ChromaDB
        collection_name: Название коллекции
        model_name: Модель для эмбеддингов
    """
    print("=" * 60)
    print("МИГРАЦИЯ ИЗ FAISS В CHROMADB")
    print("=" * 60)

    # 1. Загрузка FAISS данных
    print("1. Загрузка FAISS индекса...")
    index = faiss.read_index(faiss_index_path)

    # Получаем все векторы из FAISS
    total_vectors = index.ntotal
    dimension = index.d

    # Извлекаем все векторы
    vectors = []
    batch_size = 1000

    for i in range(0, total_vectors, batch_size):
        end_idx = min(i + batch_size, total_vectors)

        # Создаем запрос для извлечения векторов
        query_vector = np.zeros((1, dimension), dtype='float32')
        distances, indices = index.search(query_vector, end_idx)

        # FAISS не предоставляет прямой способ извлечения всех векторов
        # Вместо этого нам нужно хранить оригинальные тексты

    print("2. Загрузка метаданных...")
    with open(metadata_path, 'rb') as f:
        metadata_list = pickle.load(f)

    print(f"Загружено метаданных: {len(metadata_list)}")

    # 3. Инициализация ChromaDB
    print("3. Инициализация ChromaDB...")
    embed_function = get_embedding_function(model_name)

    chroma_manager = ChromaDBManager(
        persist_directory=chroma_persist_dir,
        collection_name=collection_name,
        embedding_function=embed_function
    )

    # Создаем коллекцию
    chroma_manager.create_collection(
        metadata={
            "migrated_from": "faiss",
            "original_index": faiss_index_path,
            "total_documents": len(metadata_list)
        }
    )

    # 4. Добавление документов (необходимы оригинальные тексты)
    print("4. Добавление документов в ChromaDB...")

    # Извлекаем тексты из метаданных
    documents = []
    chroma_metadatas = []

    for i, meta in enumerate(metadata_list):
        text = meta.get('original_text', meta.get('text', ''))
        if not text:
            print(f"Внимание: документ {i} не содержит текста")
            continue

        documents.append(text)

        chroma_metadata = meta.copy()
        # Удаляем длинный текст из метаданных (он будет в documents)
        if 'original_text' in chroma_metadata:
            del chroma_metadata['original_text']
        if 'text' in chroma_metadata and len(chroma_metadata['text']) > 500:
            chroma_metadata['text'] = chroma_metadata['text'][:500] + "..."

        chroma_metadatas.append(chroma_metadata)

    # Добавляем в ChromaDB
    ids = chroma_manager.add_documents(
        documents=documents,
        metadatas=chroma_metadatas
    )

    # 5. Сохранение
    print("5. Сохранение ChromaDB...")
    chroma_manager.save()

    # Сохраняем информацию о миграции
    migration_info = {
        "migrated_at": str(datetime.now()),
        "source_faiss_index": faiss_index_path,
        "source_metadata": metadata_path,
        "target_chromadb": chroma_persist_dir,
        "collection_name": collection_name,
        "total_documents_migrated": len(documents),
        "model_used": model_name
    }

    info_path = Path(chroma_persist_dir) / "migration_info.json"
    with open(info_path, 'w', encoding='utf-8') as f:
        json.dump(migration_info, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("МИГРАЦИЯ ЗАВЕРШЕНА")
    print("=" * 60)
    print(f"Документов мигрировано: {len(documents)}")
    print(f"ChromaDB сохранена в: {chroma_persist_dir}")
    print(f"Коллекция: {collection_name}")
    print(f"Информация о миграции: {info_path}")

    return True


if __name__ == "__main__":
    from datetime import datetime

    migrate_faiss_to_chromadb(
        faiss_index_path="outputs/faiss_index.bin",
        metadata_path="outputs/metadata.pkl",
        chroma_persist_dir="outputs/chroma_db",
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )