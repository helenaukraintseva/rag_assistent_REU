"""
build_vector_store.py - Создание векторной БД на основе результатов экспериментов
Оптимизировано с учетом:
- Модель эмбеддингов: intfloat/multilingual-e5-small (recall@5=0.82)
- Векторная БД: Chroma (встраиваемая)
- Размерность: 384
- top_k = 5 (оптимальное значение из эксперимента)
"""

import json
import re
import hashlib
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
import time
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OptimizedVectorStore:
    """Оптимизированное создание векторного хранилища на основе экспериментов"""

    def __init__(self,
                 embedding_model: str = "intfloat/multilingual-e5-small",
                 chunk_size: int = 800,
                 overlap: int = 150,
                 db_path: str = "./chroma_db_optimized"):

        self.embedding_model_name = embedding_model
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.db_path = db_path
        self.model = None
        self.client = None
        self.collection = None

        # Статистика производительности (как в вашем отчете)
        self.stats = {
            'total_chunks': 0,
            'total_documents': 0,
            'embedding_time': 0,
            'indexing_time': 0,
            'avg_chunk_size': 0
        }

    def load_embedding_model(self):
        """Загрузка модели эмбеддингов с оптимизацией"""
        logger.info(f"Загрузка модели эмбеддингов: {self.embedding_model_name}")

        start_time = time.time()

        # Оптимизации для CPU (как в вашем отчете)
        self.model = SentenceTransformer(self.embedding_model_name)
        self.model.eval()  # Режим оценки
        self.model.to('cpu')  # Используем CPU (как в вашей конфигурации)

        load_time = time.time() - start_time
        logger.info(f"Модель загружена за {load_time:.2f} секунд")

        return self.model

    def preprocess_text(self, text: str, is_query: bool = False) -> str:
        """Предобработка текста с добавлением префиксов (как в документации E5)"""
        # Очистка текста
        text = text.strip()

        # Добавление префиксов для модели E5
        if is_query:
            return f"query: {text}"
        else:
            return f"passage: {text}"

    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Батчевая генерация эмбеддингов
        batch_size=32 выбран экспериментально (как в вашем отчете)
        """
        logger.info(f"Генерация эмбеддингов для {len(texts)} текстов (batch_size={batch_size})")

        # Предобработка текстов
        processed_texts = [self.preprocess_text(text, is_query=False) for text in texts]

        start_time = time.time()

        # Батчевое кодирование
        embeddings = []
        for i in range(0, len(processed_texts), batch_size):
            batch = processed_texts[i:i + batch_size]
            batch_embeddings = self.model.encode(batch, show_progress_bar=True)
            embeddings.extend(batch_embeddings)

        elapsed_time = time.time() - start_time
        logger.info(f"Эмбеддинги сгенерированы за {elapsed_time:.2f} секунд")

        self.stats['embedding_time'] = elapsed_time

        return embeddings

    def chunk_text_smart(self, text: str, metadata: Dict = None) -> List[Dict]:
        """
        Умное разбиение текста на чанки (на основе вашего подхода)
        """
        if len(text) <= self.chunk_size:
            return [{
                'text': text,
                'chunk_index': 0,
                'total_chunks': 1,
                'chunk_size_chars': len(text),
                'metadata': metadata or {}
            }]

        # Разбиваем на предложения
        sentences = re.split(r'(?<=[.!?])\s+(?=[А-ЯA-Z0-9«"])', text)

        chunks = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence_size = len(sentence)

            if current_size + sentence_size > self.chunk_size and current_chunk:
                # Сохраняем текущий чанк
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'chunk_index': len(chunks),
                    'total_chunks': 0,
                    'chunk_size_chars': len(chunk_text),
                    'metadata': metadata or {}
                })

                # Перекрытие: оставляем последние предложения
                overlap_size = 0
                overlap_sentences = []
                for s in reversed(current_chunk):
                    if overlap_size + len(s) <= self.overlap:
                        overlap_sentences.insert(0, s)
                        overlap_size += len(s)
                    else:
                        break

                current_chunk = overlap_sentences
                current_size = overlap_size

            current_chunk.append(sentence)
            current_size += sentence_size

        # Добавляем последний чанк
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'chunk_index': len(chunks),
                'total_chunks': 0,
                'chunk_size_chars': len(chunk_text),
                'metadata': metadata or {}
            })

        # Обновляем total_chunks
        for chunk in chunks:
            chunk['total_chunks'] = len(chunks)

        return chunks

    def load_chunks_from_json(self, json_path: str) -> List[Dict]:
        """
        Загрузка и разбиение чанков из JSON файла
        """
        logger.info(f"Загрузка данных из {json_path}")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        all_chunks = []

        for idx, (doc_id, document, metadata) in enumerate(zip(
                data.get('ids', []),
                data.get('documents', []),
                data.get('metadatas', [])
        ), 1):

            doc_name = metadata.get('document_name', metadata.get('question', f'Document_{idx}'))
            logger.info(f"Обработка [{idx}/{len(data.get('documents', []))}]: {doc_name[:50]}...")

            # Разбиваем на чанки
            chunks = self.chunk_text_smart(document, metadata)

            for chunk in chunks:
                chunk['original_doc_id'] = doc_id
                chunk['doc_name'] = doc_name
                chunk['doc_type'] = metadata.get('type', 'document')

            all_chunks.extend(chunks)
            self.stats['total_documents'] += 1

        self.stats['total_chunks'] = len(all_chunks)
        self.stats['avg_chunk_size'] = sum(c['chunk_size_chars'] for c in all_chunks) // len(
            all_chunks) if all_chunks else 0

        logger.info(f"Загружено {self.stats['total_chunks']} чанков из {self.stats['total_documents']} документов")
        logger.info(f"Средний размер чанка: {self.stats['avg_chunk_size']} символов")

        return all_chunks

    def create_chroma_collection(self, collection_name: str = "university_documents"):
        """
        Создание коллекции в Chroma DB
        """
        logger.info(f"Создание Chroma DB в {self.db_path}")

        # Создаем клиент с постоянным хранилищем
        self.client = chromadb.PersistentClient(path=self.db_path)

        # Удаляем существующую коллекцию при необходимости
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Удалена существующая коллекция {collection_name}")
        except:
            pass

        # Создаем новую коллекцию (без встроенной функции эмбеддингов, т.к. мы передаем готовые)
        self.collection = self.client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine", "description": "University documents for RAG system"}
        )

        logger.info(f"Создана коллекция {collection_name}")

        return self.collection

    def add_chunks_to_chroma(self, chunks: List[Dict]):
        """
        Добавление чанков в Chroma DB с оптимизацией по батчам
        """
        logger.info(f"Добавление {len(chunks)} чанков в Chroma DB")

        start_time = time.time()

        # Подготовка данных
        ids = []
        documents = []
        metadatas = []
        embeddings = []

        for chunk in chunks:
            # Генерация уникального ID
            chunk_hash = hashlib.md5(chunk['text'].encode()).hexdigest()[:8]
            chunk_id = f"{chunk['original_doc_id']}_chunk_{chunk['chunk_index']:03d}_{chunk_hash}"

            ids.append(chunk_id)
            documents.append(chunk['text'])

            # Подготовка метаданных (как в вашем отчете)
            metadata = {
                'doc_title': chunk.get('doc_name', 'Unknown'),
                'doc_type': chunk.get('doc_type', 'unknown'),
                'chunk_index': chunk['chunk_index'],
                'total_chunks': chunk['total_chunks'],
                'original_doc_id': chunk['original_doc_id'],
                'chunk_size_chars': chunk['chunk_size_chars']
            }

            # Добавляем дополнительную информацию, если есть
            if 'document_name' in chunk.get('metadata', {}):
                metadata['pdf_link'] = chunk['metadata'].get('pdf_link', '')

            metadatas.append(metadata)

        # Генерация эмбеддингов
        logger.info("Генерация эмбеддингов для всех чанков...")
        embeddings = self.generate_embeddings_batch(documents)

        # Добавление в Chroma батчами
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_docs = documents[i:i + batch_size]
            batch_metas = metadatas[i:i + batch_size]
            batch_embs = embeddings[i:i + batch_size]

            self.collection.add(
                ids=batch_ids,
                documents=batch_docs,
                embeddings=batch_embs,
                metadatas=batch_metas
            )

            logger.info(f"Добавлено {min(i + batch_size, len(ids))}/{len(ids)} чанков")

        self.stats['indexing_time'] = time.time() - start_time

        logger.info(f"Загрузка завершена за {self.stats['indexing_time']:.2f} секунд")
        logger.info(f"Всего в БД: {self.collection.count()} записей")

    def verify_indexing_quality(self):
        """
        Проверка качества индексации (как в вашем отчете)
        """
        logger.info("Проверка качества индексации...")

        # Выборочная проверка метаданных
        sample_ids = self.collection.get()['ids'][:5]
        samples = self.collection.get(ids=sample_ids)

        for i, (doc, metadata) in enumerate(zip(samples['documents'], samples['metadatas'])):
            logger.info(f"Образец {i + 1}:")
            logger.info(f"  - Документ: {metadata.get('doc_title', 'Unknown')}")
            logger.info(f"  - Тип: {metadata.get('doc_type', 'unknown')}")
            logger.info(f"  - Чанк {metadata.get('chunk_index', 0)}/{metadata.get('total_chunks', 1)}")
            logger.info(f"  - Длина текста: {len(doc)} символов")

        # Тестирование производительности поиска (как в вашем отчете)
        test_queries = [
            "Как получить стипендию?",
            "Расписание занятий",
            "Правила перевода"
        ]

        import time
        search_times = []

        for query in test_queries:
            # Векторизация запроса
            query_vector = self.model.encode([self.preprocess_text(query, is_query=True)])[0]

            start_time = time.time()
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=5
            )
            search_time = time.time() - start_time
            search_times.append(search_time)

            logger.info(f"Поиск '{query[:30]}...' выполнен за {search_time * 1000:.2f} мс")

        avg_search_time = sum(search_times) / len(search_times)
        logger.info(f"Среднее время поиска: {avg_search_time * 1000:.2f} мс")

        return avg_search_time

    def save_stats(self, stats_path: str = "vector_store_stats.json"):
        """Сохранение статистики"""
        self.stats['chroma_db_size'] = self.get_db_size()

        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)

        logger.info(f"Статистика сохранена в {stats_path}")

        # Вывод итоговой статистики
        print("\n" + "=" * 60)
        print("📊 ИТОГОВАЯ СТАТИСТИКА ВЕКТОРНОЙ БД")
        print("=" * 60)
        print(f"Всего документов: {self.stats['total_documents']}")
        print(f"Всего чанков: {self.stats['total_chunks']}")
        print(f"Средний размер чанка: {self.stats['avg_chunk_size']} символов")
        print(f"Время генерации эмбеддингов: {self.stats['embedding_time']:.2f} сек")
        print(f"Время индексации: {self.stats['indexing_time']:.2f} сек")
        print(f"Размер БД на диске: {self.stats['chroma_db_size']}")
        print("=" * 60)

    def get_db_size(self) -> str:
        """Получение размера БД на диске"""
        import shutil
        db_size = shutil.disk_usage(self.db_path) if Path(self.db_path).exists() else (0, 0, 0)

        size_bytes = sum(f.stat().st_size for f in Path(self.db_path).rglob('*') if f.is_file())

        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"

    def run_full_pipeline(self, json_path: str, collection_name: str = "university_documents"):
        """
        Запуск полного конвейера создания векторной БД
        """
        logger.info("=" * 60)
        logger.info("ЗАПУСК КОНВЕЙЕРА СОЗДАНИЯ ВЕКТОРНОЙ БД")
        logger.info("=" * 60)

        # Шаг 1: Загрузка модели эмбеддингов
        self.load_embedding_model()

        # Шаг 2: Загрузка и разбиение чанков
        chunks = self.load_chunks_from_json(json_path)

        # Шаг 3: Создание коллекции Chroma
        self.create_chroma_collection(collection_name)

        # Шаг 4: Добавление чанков в БД
        self.add_chunks_to_chroma(chunks)

        # Шаг 5: Проверка качества
        avg_search_time = self.verify_indexing_quality()

        # Шаг 6: Сохранение статистики
        self.save_stats()

        return self.collection, avg_search_time


# Основная функция
def main():
    """Основная функция для создания векторной БД"""

    # Параметры (на основе ваших экспериментов)
    CONFIG = {
        "json_path": "chroma_data_with_qa.json",
        "db_path": "./chroma_db_optimized",
        "collection_name": "university_documents",
        "embedding_model": "intfloat/multilingual-e5-small",  # recall@5=0.82
        "chunk_size": 800,  # Оптимальный размер из экспериментов
        "overlap": 150  # Перекрытие для сохранения контекста
    }

    # Проверка существования JSON файла
    if not Path(CONFIG["json_path"]).exists():
        logger.error(f"Файл {CONFIG['json_path']} не найден!")
        return

    # Создание векторного хранилища
    vector_store = OptimizedVectorStore(
        embedding_model=CONFIG["embedding_model"],
        chunk_size=CONFIG["chunk_size"],
        overlap=CONFIG["overlap"],
        db_path=CONFIG["db_path"]
    )

    # Запуск конвейера
    collection, avg_search_time = vector_store.run_full_pipeline(
        json_path=CONFIG["json_path"],
        collection_name=CONFIG["collection_name"]
    )

    logger.info("✅ Векторная БД успешно создана!")


if __name__ == "__main__":
    main()