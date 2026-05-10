import json
import re
import hashlib
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from chromadb.utils import embedding_functions


# ============= 1. ЧАСТЬ: РАЗБИЕНИЕ ТЕКСТА НА ЧАНКИ =============

class SmartChunker:
    """Умное разбиение текста на семантически связанные чанки"""

    def __init__(self, chunk_size: int = 800, overlap: int = 150):
        """
        Args:
            chunk_size: оптимальный размер чанка для embedding моделей
            overlap: перекрытие для сохранения контекста
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split_into_sentences(self, text: str) -> List[str]:
        """Разбивает текст на предложения (поддержка русского языка)"""
        # Паттерн для русских и английских предложений
        sentences = re.split(r'(?<=[.!?])\s+(?=[А-ЯA-Z0-9«"])', text)
        return [s.strip() for s in sentences if s.strip()]

    def chunk_text(self, text: str, doc_metadata: Dict = None) -> List[Dict]:
        """
        Основной метод разбиения текста на чанки

        Returns:
            Список чанков с метаданными
        """
        if len(text) <= self.chunk_size:
            return [{
                'text': text,
                'chunk_index': 0,
                'total_chunks': 1,
                'chunk_size_chars': len(text),
                'chunk_size_words': len(text.split()),
                'metadata': doc_metadata or {}
            }]

        # Разбиваем на предложения
        sentences = self.split_into_sentences(text)

        chunks = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence_size = len(sentence)

            # Если предложение слишком большое, разбиваем его
            if sentence_size > self.chunk_size:
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, len(chunks), doc_metadata))
                    current_chunk = []
                    current_size = 0

                # Разбиваем длинное предложение на части
                parts = self._split_long_sentence(sentence)
                for part in parts:
                    chunks.append(self._create_chunk([part], len(chunks), doc_metadata))
                continue

            # Если добавление предложения превышает лимит
            if current_size + sentence_size > self.chunk_size and current_chunk:
                chunks.append(self._create_chunk(current_chunk, len(chunks), doc_metadata))

                # Сохраняем перекрытие из последних предложений
                overlap_sentences = self._get_overlap_sentences(current_chunk)
                current_chunk = overlap_sentences
                current_size = sum(len(s) for s in overlap_sentences)

            current_chunk.append(sentence)
            current_size += sentence_size

        # Добавляем последний чанк
        if current_chunk:
            chunks.append(self._create_chunk(current_chunk, len(chunks), doc_metadata))

        # Обновляем total_chunks в метаданных
        for chunk in chunks:
            chunk['total_chunks'] = len(chunks)

        return chunks

    def _split_long_sentence(self, sentence: str) -> List[str]:
        """Разбивает длинное предложение на части по запятым и союзам"""
        # Разбиваем по запятой, точке с запятой, двоеточию
        parts = re.split(r'(?<=[,;:])\s+', sentence)

        if len(parts) <= 1:
            # Если нет подходящих разделителей, разбиваем по словам
            words = sentence.split()
            parts = []
            current_part = []
            current_size = 0

            for word in words:
                if current_size + len(word) > self.chunk_size and current_part:
                    parts.append(' '.join(current_part))
                    current_part = [word]
                    current_size = len(word)
                else:
                    current_part.append(word)
                    current_size += len(word) + 1

            if current_part:
                parts.append(' '.join(current_part))

        return parts

    def _get_overlap_sentences(self, sentences: List[str]) -> List[str]:
        """Получает последние предложения для перекрытия"""
        overlap_size = 0
        overlap_sentences = []

        for sentence in reversed(sentences):
            if overlap_size + len(sentence) <= self.overlap:
                overlap_sentences.insert(0, sentence)
                overlap_size += len(sentence)
            else:
                break

        return overlap_sentences

    def _create_chunk(self, sentences: List[str], index: int, metadata: Dict) -> Dict:
        """Создает структуру чанка с метаданными"""
        chunk_text = ' '.join(sentences)

        return {
            'text': chunk_text,
            'chunk_index': index,
            'total_chunks': 0,  # Будет обновлено позже
            'chunk_size_chars': len(chunk_text),  # Добавлено
            'chunk_size_words': len(chunk_text.split()),  # Добавлено
            'metadata': metadata or {}
        }


# ============= 2. ЧАСТЬ: ОБРАБОТКА JSON И СОЗДАНИЕ ЧАНКОВ =============

def process_json_with_chunking(input_json_path: str,
                               output_json_path: str = None,
                               chunk_size: int = 800,
                               overlap: int = 150) -> Dict:
    """
    Обрабатывает JSON файл и разбивает документы на чанки

    Args:
        input_json_path: путь к входному JSON
        output_json_path: путь для сохранения результата
        chunk_size: размер чанка в символах
        overlap: перекрытие между чанками
    """

    # Загружаем исходный JSON
    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"\n📖 Загружен JSON: {input_json_path}")
    print(f"   Документов: {len(data.get('documents', []))}")

    # Инициализируем чанкер
    chunker = SmartChunker(chunk_size=chunk_size, overlap=overlap)

    # Новые данные
    chunked_ids = []
    chunked_documents = []
    chunked_metadatas = []

    stats = {
        'total_original': len(data.get('documents', [])),
        'total_chunks': 0,
        'avg_chunk_size': 0
    }

    for idx, (doc_id, document, metadata) in enumerate(zip(
            data.get('ids', []),
            data.get('documents', []),
            data.get('metadatas', [])
    ), 1):

        # Получаем название документа
        doc_name = metadata.get('document_name', metadata.get('question', f'Document_{idx}'))
        print(f"\n📄 [{idx}/{stats['total_original']}] {doc_name[:50]}...")
        print(f"   Размер: {len(document):,} символов")

        # Разбиваем на чанки
        try:
            chunks = chunker.chunk_text(document, metadata)
            print(f"   → Разбито на {len(chunks)} чанков")
            stats['total_chunks'] += len(chunks)
        except Exception as e:
            print(f"   ❌ Ошибка разбиения: {e}")
            continue

        # Добавляем чанки
        for chunk in chunks:
            # Генерируем уникальный ID для чанка
            chunk_hash = hashlib.md5(chunk['text'].encode()).hexdigest()[:8]
            chunk_id = f"{doc_id}_chunk_{chunk['chunk_index']:03d}_{chunk_hash}"

            chunked_ids.append(chunk_id)
            chunked_documents.append(chunk['text'])

            # Обогащаем метаданные
            enriched_metadata = {
                **chunk['metadata'],
                'is_chunk': True,
                'chunk_index': chunk['chunk_index'],
                'total_chunks_for_doc': chunk['total_chunks'],
                'original_document_id': doc_id,
                'chunk_size_chars': chunk.get('chunk_size_chars', len(chunk['text'])),
                'chunk_size_words': chunk.get('chunk_size_words', len(chunk['text'].split()))
            }

            chunked_metadatas.append(enriched_metadata)

    # Создаем выходную структуру
    output_data = {
        "metadata": {
            **data.get('metadata', {}),
            "chunking_info": {
                "method": "semantic_smart",
                "chunk_size": chunk_size,
                "overlap": overlap,
                "original_documents": stats['total_original'],
                "total_chunks": stats['total_chunks'],
                "avg_chunks_per_doc": stats['total_chunks'] / stats['total_original'] if stats[
                                                                                             'total_original'] > 0 else 0
            }
        },
        "ids": chunked_ids,
        "documents": chunked_documents,
        "metadatas": chunked_metadatas
    }

    # Сохраняем результат
    if output_json_path is None:
        output_json_path = input_json_path.replace('.json', '_chunked.json')

    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # Выводим статистику
    if chunked_documents:
        avg_size = sum(len(d) for d in chunked_documents) // len(chunked_documents)
    else:
        avg_size = 0

    print(f"\n{'=' * 60}")
    print(f"✅ Разбиение завершено!")
    print(f"📊 Статистика:")
    print(f"   Исходных документов: {stats['total_original']}")
    print(f"   Получено чанков: {stats['total_chunks']}")
    print(f"   Средний размер чанка: {avg_size:,} символов")
    print(f"   Сохранено в: {output_json_path}")
    print(f"{'=' * 60}")

    return output_data


# ============= 3. ЧАСТЬ: ЗАГРУЗКА В CHROMA DB =============

def create_chromadb_from_chunks(json_path: str,
                                db_path: str = "chroma_db",
                                collection_name: str = "documents",
                                force_recreate: bool = True):
    """
    Создает Chroma DB из разбитых на чанки документов

    Args:
        json_path: путь к JSON файлу с чанками
        db_path: путь для сохранения БД
        collection_name: имя коллекции
        force_recreate: пересоздать БД
    """

    # Загружаем данные
    print(f"\n📖 Загрузка чанков из {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    ids = data.get('ids', [])
    documents = data.get('documents', [])
    metadatas = data.get('metadatas', [])

    print(f"   Загружено {len(documents)} чанков")

    # Создаем Chroma клиент
    db_full_path = Path(db_path)
    if force_recreate and db_full_path.exists():
        import shutil
        shutil.rmtree(db_full_path)
        print(f"🗑️  Удалена существующая БД")

    # Используем мультиязычную модель для эмбеддингов
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="intfloat/multilingual-e5-small"  # Лучшая для русского языка
    )

    client = chromadb.PersistentClient(path=db_path)

    # Удаляем старую коллекцию при необходимости
    try:
        client.delete_collection(collection_name)
    except:
        pass

    # Создаем новую коллекцию
    collection = client.create_collection(
        name=collection_name,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )

    print(f"🔧 Создана коллекция: {collection_name}")

    # Добавляем чанки пакетами
    batch_size = 100
    total_added = 0

    for i in range(0, len(documents), batch_size):
        batch_ids = ids[i:i + batch_size]
        batch_docs = documents[i:i + batch_size]
        batch_metas = metadatas[i:i + batch_size]

        collection.add(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_metas
        )

        total_added += len(batch_ids)
        print(f"   Добавлено {total_added}/{len(documents)} чанков", end='\r')

    print(f"\n✅ Загружено {collection.count()} чанков в Chroma DB")
    print(f"   Путь: {db_path}")
    print(f"   Размер БД: {get_db_size(db_path)}")

    return client, collection


def get_db_size(db_path: str) -> str:
    """Возвращает размер БД в удобном формате"""
    db_path_obj = Path(db_path)
    if not db_path_obj.exists():
        return "0 B"

    total_size = sum(f.stat().st_size for f in db_path_obj.rglob('*') if f.is_file())

    for unit in ['B', 'KB', 'MB', 'GB']:
        if total_size < 1024:
            return f"{total_size:.2f} {unit}"
        total_size /= 1024
    return f"{total_size:.2f} TB"


# ============= 4. ЧАСТЬ: ТЕСТИРОВАНИЕ ПОИСКА =============

def test_search(collection, query: str, n_results: int = 3):
    """Тестирует поиск по БД"""
    print(f"\n🔍 Поиск: '{query}'")
    print("-" * 60)

    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )

    for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
    ), 1):
        # Преобразуем расстояние в оценку релевантности
        relevance = (1 - distance) * 100

        # Получаем название документа
        doc_name = metadata.get('document_name', metadata.get('question', 'Unknown'))
        chunk_info = f" (Чанк {metadata.get('chunk_index', 0) + 1}/{metadata.get('total_chunks_for_doc', 1)})"

        print(f"\n{i}. {doc_name}{chunk_info}")
        print(f"   Релевантность: {relevance:.1f}%")

        # Показываем фрагмент ответа
        preview = doc[:300] + "..." if len(doc) > 300 else doc
        print(f"   Ответ: {preview}")


def interactive_search(collection):
    """Интерактивный режим поиска"""
    print(f"\n{'=' * 60}")
    print("💬 ИНТЕРАКТИВНЫЙ ПОИСК")
    print("   Введите вопрос или 'quit' для выхода")
    print(f"{'=' * 60}")

    while True:
        query = input("\n❓ Вопрос: ").strip()

        if query.lower() in ['quit', 'exit', 'q']:
            print("👋 До свидания!")
            break
        elif query:
            test_search(collection, query, n_results=3)


# ============= 5. ЧАСТЬ: ОСНОВНОЙ ПРОЦЕСС =============

def find_input_json():
    """Автоматически находит JSON файл для обработки"""

    # Приоритеты поиска
    possible_names = [
        "chroma_data_with_qa.json",
        "chroma_data.json",
        "qa_database.json",
        "chroma_data_chunked.json"
    ]

    # Ищем файлы в текущей директории
    json_files = list(Path(".").glob("*.json"))

    # Сначала проверяем по приоритетным именам
    for name in possible_names:
        if Path(name).exists():
            print(f"✅ Найден файл: {name}")
            return name

    # Если нет, берем первый JSON файл
    if json_files:
        first_json = json_files[0]
        print(f"✅ Использую файл: {first_json}")
        return str(first_json)

    # Если ничего не найдено
    print("❌ JSON файл не найден!")
    return None


def main():
    """Главная функция - полный пайплайн обработки"""

    print("=" * 60)
    print("🚀 RAG ПАЙПЛАЙН: ОБРАБОТКА ДОКУМЕНТОВ")
    print("=" * 60)

    # Автоматически находим JSON файл
    input_json = find_input_json()
    if not input_json:
        print("Пожалуйста, создайте JSON файл с документами")
        return

    print(f"\n📁 Обработка файла: {input_json}")

    # Параметры
    CHUNK_SIZE = 1000  # Увеличил для ваших больших документов
    OVERLAP = 200  # Увеличил перекрытие
    COLLECTION_NAME = "university_knowledge_base"

    # Шаг 1: Разбиваем на чанки
    print("\n📌 ШАГ 1: РАЗБИЕНИЕ НА ЧАНКИ")
    print("-" * 60)

    try:
        chunked_json = process_json_with_chunking(
            input_json_path=input_json,
            chunk_size=CHUNK_SIZE,
            overlap=OVERLAP
        )
    except Exception as e:
        print(f"\n❌ Ошибка при разбиении: {e}")
        print("   Проверьте структуру JSON файла")
        return

    # Шаг 2: Создаем Chroma DB
    print("\n📌 ШАГ 2: СОЗДАНИЕ VECTOR DATABASE")
    print("-" * 60)

    try:
        # Используем разбитый JSON
        chunked_json_path = input_json.replace('.json', '_chunked.json')
        client, collection = create_chromadb_from_chunks(
            json_path=chunked_json_path,
            db_path="chroma_db_optimized",
            collection_name=COLLECTION_NAME,
            force_recreate=True
        )
    except Exception as e:
        print(f"\n❌ Ошибка при создании БД: {e}")
        return

    # Шаг 3: Тестируем поиск
    print("\n📌 ШАГ 3: ТЕСТИРОВАНИЕ ПОИСКА")
    print("-" * 60)

    # Примеры вопросов
    test_queries = [
        "коллективный договор",
        "изменения в устав",
        "правила внутреннего распорядка"
    ]

    for query in test_queries:
        test_search(collection, query, n_results=2)

    # Шаг 4: Интерактивный режим
    interactive_search(collection)


# ============= ЗАПУСК =============

if __name__ == "__main__":
    import sys

    # Выбор режима
    if len(sys.argv) > 1 and sys.argv[1] == "--chunk-only":
        # Только разбиение на чанки
        input_json = find_input_json()
        if input_json:
            process_json_with_chunking(
                input_json_path=input_json,
                chunk_size=1000,
                overlap=200
            )
    else:
        # Полный пайплайн
        main()