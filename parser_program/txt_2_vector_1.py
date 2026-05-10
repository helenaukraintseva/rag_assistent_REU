import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
import re
from datetime import datetime
import pickle


class DocumentProcessorForVectorDB:
    """
    Класс для обработки PDF-файлов в формат, удобный для векторной БД.
    Поддерживает чанкирование, извлечение метаданных и создание эмбеддингов.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Инициализация процессора документов.

        Args:
            chunk_size (int): Размер чанка в символах
            chunk_overlap (int): Перекрытие между чанками
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.documents = []

    def clean_text_for_rag(self, text: str) -> str:
        """
        Очищает текст для использования в RAG.

        Args:
            text (str): Исходный текст

        Returns:
            str: Очищенный текст
        """
        if not text:
            return ""

        # Удаляем управляющие символы
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

        # Нормализуем пробелы
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        # Очищаем строки
        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        text = '\n'.join(lines)
        text = text.strip()

        # Нормализуем символы
        text = re.sub(r'[—–―]', '-', text)
        text = text.replace('\u00a0', ' ')
        text = text.replace('\u200b', '')
        text = text.replace('\ufeff', '')

        # Нормализуем кавычки
        text = re.sub(r'[«»″„“]', '"', text)
        text = re.sub(r'[‘’‛]', "'", text)

        return text

    def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Разбивает текст на чанки с перекрытием.

        Args:
            text (str): Исходный текст
            metadata (dict): Метаданные документа

        Returns:
            list: Список чанков с метаданными
        """
        if not text:
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + self.chunk_size, text_length)

            # Стараемся разбить по границе предложения или абзаца
            if end < text_length:
                # Ищем конец предложения в пределах последних 200 символов
                search_start = max(end - 200, start)
                last_period = text.rfind('.', search_start, end)
                last_newline = text.rfind('\n', search_start, end)

                # Выбираем лучшую границу для разбиения
                if last_period > search_start and (last_newline <= search_start or last_period > last_newline):
                    end = last_period + 1
                elif last_newline > search_start:
                    end = last_newline + 1

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    'chunk_id': len(chunks),
                    'chunk_start': start,
                    'chunk_end': end,
                    'chunk_size': len(chunk_text)
                })

                chunks.append({
                    'text': chunk_text,
                    'metadata': chunk_metadata
                })

            start = end - self.chunk_overlap if end < text_length else end

        return chunks

    def extract_metadata_from_filename(self, filename: str, filepath: Path) -> Dict[str, Any]:
        """
        Извлекает метаданные из имени файла и пути.

        Args:
            filename (str): Имя файла
            filepath (Path): Полный путь к файлу

        Returns:
            dict: Метаданные документа
        """
        metadata = {
            'source_file': filename,
            'file_path': str(filepath),
            'file_size': filepath.stat().st_size,
            'document_id': hashlib.md5(str(filepath).encode()).hexdigest(),
            'processed_date': datetime.now().isoformat()
        }

        # Извлекаем информацию из имени файла
        name_parts = filename.replace('.txt', '').split('_')

        # Определяем тип документа по имени
        if 'bak' in filename.lower():
            metadata['doc_type'] = 'бакалавриат'
        elif 'mag' in filename.lower():
            metadata['doc_type'] = 'магистратура'
        elif 'spo' in filename.lower():
            metadata['doc_type'] = 'среднее_профессиональное_образование'
        elif 'pravila' in filename.lower():
            metadata['doc_type'] = 'правила_приема'
        elif 'ustav' in filename.lower() or 'egrul' in filename.lower():
            metadata['doc_type'] = 'уставные_документы'
        elif 'dogovor' in filename.lower():
            metadata['doc_type'] = 'договоры'
        elif 'polozhenie' in filename.lower():
            metadata['doc_type'] = 'положения'
        else:
            metadata['doc_type'] = 'прочие_документы'

        # Извлекаем геолокацию если есть
        locations = ['bryansk', 'volgograd', 'voronezh', 'erevan', 'ivanovo',
                     'krasnodar', 'perm', 'smolensk', 'tula', 'sevastopol',
                     'orenburg', 'pyatigorsk', 'tashkent', 'ulan-bator', 'minsk']

        for location in locations:
            if location.lower() in filename.lower():
                metadata['location'] = location.capitalize()
                break

        return metadata

    def load_text_file(self, filepath: Path) -> Optional[str]:
        """
        Загружает текст из файла.

        Args:
            filepath (Path): Путь к текстовому файлу

        Returns:
            str or None: Содержимое файла или None при ошибке
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"  Ошибка загрузки {filepath}: {e}")
            return None

    def process_txt_files(self, input_folder: str = "rag_ready_texts") -> List[Dict[str, Any]]:
        """
        Обрабатывает все TXT файлы и подготавливает их для векторной БД.

        Args:
            input_folder (str): Папка с текстовыми файлами

        Returns:
            list: Список чанков с эмбеддингами
        """
        input_path = Path(input_folder)
        txt_files = list(input_path.glob("*.txt"))

        # Исключаем служебные файлы
        txt_files = [f for f in txt_files if not f.name.startswith("_")]

        if not txt_files:
            print(f"❌ TXT файлы не найдены в папке '{input_folder}'")
            return []

        print(f"📁 Найдено TXT файлов: {len(txt_files)}")
        print(f"📏 Размер чанка: {self.chunk_size} символов")
        print(f"🔄 Перекрытие: {self.chunk_overlap} символов")
        print("=" * 60)

        all_chunks = []
        total_chunks = 0

        for i, txt_file in enumerate(txt_files, 1):
            print(f"[{i}/{len(txt_files)}] Обработка: {txt_file.name}")

            # Загружаем текст
            text = self.load_text_file(txt_file)

            if text:
                # Очищаем текст
                cleaned_text = self.clean_text_for_rag(text)

                # Извлекаем метаданные
                metadata = self.extract_metadata_from_filename(txt_file.name, txt_file)
                metadata['original_size'] = len(text)
                metadata['cleaned_size'] = len(cleaned_text)

                # Разбиваем на чанки
                chunks = self.chunk_text(cleaned_text, metadata)

                if chunks:
                    all_chunks.extend(chunks)
                    total_chunks += len(chunks)
                    print(f"  ✓ Создано чанков: {len(chunks)}")
                    print(f"    Текст: {len(cleaned_text):,} символов -> {len(chunks)} фрагментов")
                else:
                    print(f"  ⚠ Не удалось создать чанки")
            else:
                print(f"  ✗ Ошибка загрузки текста")

            print()

        self.documents = all_chunks
        print("=" * 60)
        print(f"✅ Всего создано чанков: {total_chunks}")

        return all_chunks

    def save_for_vector_db(self, output_folder: str = "vector_db_ready",
                           format: str = "json") -> Dict[str, Any]:
        """
        Сохраняет обработанные документы в формате, готовом для векторной БД.

        Args:
            output_folder (str): Папка для сохранения
            format (str): Формат сохранения ('json', 'pickle', 'both')

        Returns:
            dict: Статистика сохранения
        """
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)

        stats = {
            'total_chunks': len(self.documents),
            'total_characters': sum(len(chunk['text']) for chunk in self.documents),
            'avg_chunk_size': 0,
            'doc_types': {}
        }

        if self.documents:
            stats['avg_chunk_size'] = stats['total_characters'] // len(self.documents)

            # Статистика по типам документов
            for chunk in self.documents:
                doc_type = chunk['metadata'].get('doc_type', 'unknown')
                stats['doc_types'][doc_type] = stats['doc_types'].get(doc_type, 0) + 1

        # Сохраняем в JSON
        if format in ['json', 'both']:
            json_path = output_path / "documents_for_vector_db.json"

            # Подготавливаем данные для JSON
            json_data = {
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'chunk_size': self.chunk_size,
                    'chunk_overlap': self.chunk_overlap,
                    'total_chunks': stats['total_chunks'],
                    'statistics': stats
                },
                'documents': self.documents
            }

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)

            print(f"✓ JSON файл сохранён: {json_path}")

        # Сохраняем в Pickle (для Python)
        if format in ['pickle', 'both']:
            pickle_path = output_path / "documents_for_vector_db.pkl"

            with open(pickle_path, 'wb') as f:
                pickle.dump(self.documents, f)

            print(f"✓ Pickle файл сохранён: {pickle_path}")

        # Сохраняем в формат для LangChain
        langchain_path = output_path / "langchain_documents.json"
        langchain_data = []

        for chunk in self.documents:
            langchain_data.append({
                'page_content': chunk['text'],
                'metadata': chunk['metadata']
            })

        with open(langchain_path, 'w', encoding='utf-8') as f:
            json.dump(langchain_data, f, ensure_ascii=False, indent=2)

        print(f"✓ LangChain формат сохранён: {langchain_path}")

        # Сохраняем статистику
        stats_path = output_path / "processing_stats.txt"
        with open(stats_path, 'w', encoding='utf-8') as f:
            f.write("СТАТИСТИКА ОБРАБОТКИ ДОКУМЕНТОВ ДЛЯ ВЕКТОРНОЙ БД\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Дата обработки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Размер чанка: {self.chunk_size} символов\n")
            f.write(f"Перекрытие: {self.chunk_overlap} символов\n\n")
            f.write(f"Всего чанков: {stats['total_chunks']}\n")
            f.write(f"Всего символов: {stats['total_characters']:,}\n")
            f.write(f"Средний размер чанка: {stats['avg_chunk_size']} символов\n\n")
            f.write("Распределение по типам документов:\n")
            for doc_type, count in sorted(stats['doc_types'].items()):
                f.write(f"  {doc_type}: {count} чанков\n")

        print(f"✓ Статистика сохранена: {stats_path}")

        return stats

    def create_embeddings_ready_format(self, output_file: str = "embeddings_ready.json"):
        """
        Создаёт формат, готовый для генерации эмбеддингов.
        Каждый чанк имеет уникальный ID и текст.

        Args:
            output_file (str): Имя выходного файла
        """
        if not self.documents:
            print("❌ Нет обработанных документов. Сначала запустите process_txt_files()")
            return

        ready_data = []
        for i, chunk in enumerate(self.documents):
            ready_data.append({
                'id': f"chunk_{i:06d}",
                'text': chunk['text'],
                'text_length': len(chunk['text']),
                'source_file': chunk['metadata']['source_file'],
                'doc_type': chunk['metadata']['doc_type'],
                'chunk_id': chunk['metadata']['chunk_id']
            })

        output_path = Path("embeddings_ready")
        output_path.mkdir(exist_ok=True)

        # Сохраняем как JSON
        json_path = output_path / output_file
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(ready_data, f, ensure_ascii=False, indent=2)

        print(f"✓ Готово для эмбеддингов: {json_path}")
        print(f"  Всего записей: {len(ready_data)}")

        # Сохраняем также в текстовом формате для быстрого просмотра
        text_path = output_path / "all_chunks_text.txt"
        with open(text_path, 'w', encoding='utf-8') as f:
            for item in ready_data:
                f.write(f"{'=' * 60}\n")
                f.write(f"ID: {item['id']}\n")
                f.write(f"Файл: {item['source_file']}\n")
                f.write(f"Тип: {item['doc_type']}\n")
                f.write(f"Длина: {item['text_length']} символов\n")
                f.write(f"{'-' * 60}\n")
                f.write(item['text'])
                f.write(f"\n\n")

        print(f"✓ Тексты всех чанков: {text_path}")

        return ready_data


class VectorDBPreparator:
    """
    Класс для подготовки данных для конкретных векторных БД.
    """

    @staticmethod
    def prepare_for_chroma(documents: List[Dict[str, Any]],
                           collection_name: str = "rea_documents") -> Dict[str, Any]:
        """
        Подготавливает данные для ChromaDB.

        Args:
            documents (list): Список чанков с текстами и метаданными
            collection_name (str): Имя коллекции

        Returns:
            dict: Данные в формате ChromaDB
        """
        chroma_data = {
            'collection_name': collection_name,
            'documents': [],
            'metadatas': [],
            'ids': []
        }

        for i, doc in enumerate(documents):
            chroma_data['documents'].append(doc['text'])
            chroma_data['metadatas'].append(doc['metadata'])
            chroma_data['ids'].append(f"id_{i:06d}")

        return chroma_data

    @staticmethod
    def prepare_for_faiss(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Подготавливает данные для FAISS.

        Args:
            documents (list): Список чанков с текстами

        Returns:
            dict: Данные в формате FAISS
        """
        return {
            'texts': [doc['text'] for doc in documents],
            'metadatas': [doc['metadata'] for doc in documents]
        }

    @staticmethod
    def prepare_for_qdrant(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Подготавливает данные для Qdrant.

        Args:
            documents (list): Список чанков с текстами

        Returns:
            list: Данные в формате Qdrant
        """
        qdrant_data = []
        for i, doc in enumerate(documents):
            qdrant_data.append({
                'id': i,
                'payload': doc['metadata'],
                'vector': None,  # Эмбеддинги будут добавлены позже
                'text': doc['text']
            })

        return qdrant_data


def create_sample_embedding_code(output_dir: str = "vector_db_ready"):
    """
    Создаёт пример кода для генерации эмбеддингов и загрузки в векторную БД.

    Args:
        output_dir (str): Директория для сохранения примеров
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    code_example = '''import json
import pickle
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions

# 1. Загрузка подготовленных документов
with open('vector_db_ready/documents_for_vector_db.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

documents = data['documents']
print(f"Загружено чанков: {len(documents)}")

# 2. Генерация эмбеддингов
model = SentenceTransformer('intfloat/multilingual-e5-large')  # или другая модель

texts = [doc['text'] for doc in documents]
embeddings = model.encode(texts, show_progress_bar=True)

print(f"Сгенерировано эмбеддингов: {len(embeddings)}")
print(f"Размерность эмбеддингов: {embeddings[0].shape[0]}")

# 3. Сохранение эмбеддингов
embedding_data = {
    'embeddings': embeddings.tolist(),
    'texts': texts,
    'metadatas': [doc['metadata'] for doc in documents]
}

with open('vector_db_ready/embeddings_with_data.pkl', 'wb') as f:
    pickle.dump(embedding_data, f)

print("✓ Эмбеддинги сохранены")

# 4. Пример загрузки в ChromaDB
client = chromadb.Client()
collection = client.create_collection(
    name="rea_documents",
    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name='intfloat/multilingual-e5-large'
    )
)

# Добавляем документы в коллекцию
batch_size = 100
for i in range(0, len(documents), batch_size):
    batch = documents[i:i+batch_size]
    collection.add(
        documents=[doc['text'] for doc in batch],
        metadatas=[doc['metadata'] for doc in batch],
        ids=[f"doc_{j:06d}" for j in range(i, i+len(batch))]
    )
    print(f"Добавлено {i+len(batch)}/{len(documents)} документов")

print("✓ Данные загружены в ChromaDB")

# 5. Тестовый поиск
query = "правила приема в бакалавриат"
results = collection.query(query_texts=[query], n_results=5)

print(f"\\nРезультаты поиска по запросу: '{query}'")
print("="*60)
for i, (doc, metadata, distance) in enumerate(zip(
    results['documents'][0], 
    results['metadatas'][0], 
    results['distances'][0]
)):
    print(f"{i+1}. {metadata['source_file']} (релевантность: {1-distance:.3f})")
    print(f"   {doc[:200]}...\\n")
'''

    code_path = output_path / "example_embedding_code.py"
    with open(code_path, 'w', encoding='utf-8') as f:
        f.write(code_example)

    print(f"✓ Пример кода создан: {code_path}")


def main():
    """
    Основная функция для обработки документов.
    """
    print("\n" + "=" * 60)
    print("🔄 ПОДГОТОВКА ДОКУМЕНТОВ ДЛЯ ВЕКТОРНОЙ БД")
    print("=" * 60 + "\n")

    # Создаём процессор документов
    processor = DocumentProcessorForVectorDB(
        chunk_size=1500,  # Размер чанка в символах
        chunk_overlap=200  # Перекрытие между чанками
    )

    # Обрабатываем TXT файлы
    chunks = processor.process_txt_files(input_folder="txt_documents_2")

    if chunks:
        # Сохраняем в форматах для векторной БД
        stats = processor.save_for_vector_db(
            output_folder="vector_db_ready",
            format="both"  # Сохраняем и в JSON, и в Pickle
        )

        # Создаём формат, готовый для эмбеддингов
        embedding_ready = processor.create_embeddings_ready_format(
            output_file="embeddings_ready_data.json"
        )

        # Создаём пример кода
        create_sample_embedding_code()

        # Выводим статистику
        print("\n" + "=" * 60)
        print("📊 ФИНАЛЬНАЯ СТАТИСТИКА")
        print("=" * 60)
        print(f"✅ Всего чанков: {stats['total_chunks']}")
        print(f"📝 Всего символов: {stats['total_characters']:,}")
        print(f"📏 Средний размер чанка: {stats['avg_chunk_size']} символов")
        print(f"\n📂 Результаты сохранены в папке: vector_db_ready/")
        print(f"   - documents_for_vector_db.json (полные данные)")
        print(f"   - documents_for_vector_db.pkl (pickle формат)")
        print(f"   - langchain_documents.json (LangChain формат)")
        print(f"   - embeddings_ready_data.json (готово для эмбеддингов)")
        print(f"   - example_embedding_code.py (пример кода)")
        print(f"   - processing_stats.txt (статистика)")

    else:
        print("\n❌ Не удалось обработать документы.")
        print("Убедитесь, что папка 'rag_ready_texts' содержит TXT файлы.")


if __name__ == "__main__":
    main()