import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
import re
from datetime import datetime
import pickle
import sys


class DocumentProcessorForVectorDB:
    """
    Класс для обработки PDF-файлов в формат, удобный для векторной БД.
    Поддерживает чанкирование, извлечение метаданных и создание эмбеддингов.
    """

    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 200):
        """
        Инициализация процессора документов.

        Args:
            chunk_size (int): Размер чанка в символах
            chunk_overlap (int): Перекрытие между чанками
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.documents = []
        self.links_data = None

    def load_links_data(self, links_module_path: str = "links") -> Dict[str, Any]:
        """
        Загружает данные из links.py для сопоставления файлов с URL и категориями.
        """
        try:
            import importlib.util

            links_file = Path(f"{links_module_path}.py")
            if links_file.exists():
                spec = importlib.util.spec_from_file_location("links", links_file)
                links_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(links_module)
                self.links_data = links_module.links
                print(f"✓ Загружены данные из {links_module_path}.py ({len(self.links_data)} категорий)")
            else:
                print(f"⚠ Файл {links_module_path}.py не найден. Ссылки не будут добавлены.")
                self.links_data = {}
        except Exception as e:
            print(f"⚠ Ошибка загрузки links.py: {e}")
            self.links_data = {}

        return self.links_data

    def find_file_metadata(self, filename: str) -> Dict[str, Any]:
        """
        Ищет в links.py метаданные для файла по его имени.
        """
        if not self.links_data:
            return {}

        search_name = filename.replace('.pdf', '').replace('.txt', '').lower()

        for category, documents in self.links_data.items():
            for doc_title, url in documents.items():
                if not url or not url.strip():
                    continue

                # Извлекаем имя файла из URL
                url_filename = Path(url).name.replace('.pdf', '').lower()
                doc_title_lower = doc_title.lower()

                # Сравниваем с искомым именем
                if (search_name == url_filename or
                        search_name in url_filename or
                        url_filename in search_name or
                        search_name in doc_title_lower or
                        doc_title_lower in search_name):
                    return {
                        'category': category,
                        'document_title': doc_title,
                        'original_url': url,
                        'matched_by': 'url_filename' if search_name in url_filename else 'title'
                    }

        return {}

    def clean_text_for_rag(self, text: str) -> str:
        """Очищает текст для использования в RAG."""
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
        """Разбивает текст на чанки с перекрытием."""
        if not text:
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + self.chunk_size, text_length)

            # Стараемся разбить по границе предложения или абзаца
            if end < text_length:
                search_start = max(end - 200, start)
                last_period = text.rfind('.', search_start, end)
                last_newline = text.rfind('\n', search_start, end)

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

    def extract_metadata_from_filename(self, filename: str, filepath: Path, category_from_folder: str = None) -> Dict[
        str, Any]:
        """
        Извлекает метаданные из имени файла, пути и данных из links.py.
        """
        metadata = {
            'source_file': filename,
            'file_path': str(filepath),
            'file_size': filepath.stat().st_size,
            'document_id': hashlib.md5(str(filepath).encode()).hexdigest(),
            'processed_date': datetime.now().isoformat()
        }

        # Добавляем категорию из структуры папок (это основная категория!)
        if category_from_folder:
            metadata['category'] = category_from_folder
            metadata['folder_category'] = category_from_folder

        # Ищем метаданные в links.py для получения URL
        links_metadata = self.find_file_metadata(filename)

        if links_metadata:
            metadata['document_title'] = links_metadata['document_title']
            metadata['original_url'] = links_metadata['original_url']
            metadata['matched_by'] = links_metadata['matched_by']
            metadata['has_link'] = True
        else:
            metadata['has_link'] = False

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
                     'orenburg', 'pyatigorsk', 'tashkent', 'ulan-bator', 'minsk',
                     'dubai', 'mos']

        for location in locations:
            if location.lower() in filename.lower():
                metadata['location'] = location.capitalize()
                break

        return metadata

    def load_text_file(self, filepath: Path) -> Optional[str]:
        """Загружает текст из файла."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"  Ошибка загрузки {filepath}: {e}")
            return None

    def process_txt_files(self, input_folder: str = "downloaded_documents",
                          links_file: str = "links") -> List[Dict[str, Any]]:
        """
        Обрабатывает все TXT файлы и подготавливает их для векторной БД.
        Рекурсивно обходит все вложенные папки.
        """
        # Загружаем данные из links.py
        self.load_links_data(links_file)

        input_path = Path(input_folder)

        # Проверяем существует ли папка
        if not input_path.exists():
            print(f"❌ Папка '{input_folder}' не найдена!")
            return []

        # Рекурсивно ищем все TXT файлы во всех подпапках
        txt_files = list(input_path.rglob("*.txt"))

        # Исключаем служебные файлы
        txt_files = [f for f in txt_files if not f.name.startswith("_")]

        if not txt_files:
            print(f"❌ TXT файлы не найдены в папке '{input_folder}'")
            print(f"   Проверьте, что в папке есть вложенные директории с TXT файлами")
            return []

        print(f"📁 Найдено TXT файлов: {len(txt_files)}")
        print(f"📂 Структура: {input_folder}/[категория]/[файлы].txt")
        print(f"📏 Размер чанка: {self.chunk_size} символов")
        print(f"🔄 Перекрытие: {self.chunk_overlap} символов")
        if self.links_data:
            print(f"🔗 Загружены данные из links.py ({len(self.links_data)} категорий)")
        print("=" * 60)

        all_chunks = []
        files_with_links = 0
        total_chunks = 0
        categories_found = set()

        for i, txt_file in enumerate(txt_files, 1):
            # Получаем относительный путь от input_folder
            rel_path = txt_file.relative_to(input_path)

            # Категория - это имя родительской папки (первая часть пути)
            if len(rel_path.parts) > 1:
                category_from_folder = rel_path.parts[0]  # Берём имя первой папки
            else:
                category_from_folder = "корневая_папка"

            categories_found.add(category_from_folder)

            print(f"[{i}/{len(txt_files)}] Обработка: {rel_path}")
            print(f"    Категория: {category_from_folder}")

            # Загружаем текст
            text = self.load_text_file(txt_file)

            if text:
                # Очищаем текст
                cleaned_text = self.clean_text_for_rag(text)

                # Извлекаем метаданные
                metadata = self.extract_metadata_from_filename(
                    txt_file.name, txt_file, category_from_folder
                )
                metadata['original_size'] = len(text)
                metadata['cleaned_size'] = len(cleaned_text)

                # Разбиваем на чанки
                chunks = self.chunk_text(cleaned_text, metadata)

                if chunks:
                    all_chunks.extend(chunks)
                    total_chunks += len(chunks)

                    has_link_status = "✅" if metadata.get('has_link') else "❌"
                    print(f"    {has_link_status} Создано чанков: {len(chunks)}")
                    print(f"      Текст: {len(cleaned_text):,} символов -> {len(chunks)} фрагментов")

                    if metadata.get('has_link'):
                        files_with_links += 1
                else:
                    print(f"    ⚠ Не удалось создать чанки")
            else:
                print(f"    ✗ Ошибка загрузки текста")

            print()

        self.documents = all_chunks
        print("=" * 60)
        print(f"✅ Всего создано чанков: {total_chunks}")
        print(f"📊 Файлов с найденными ссылками: {files_with_links}/{len(txt_files)}")
        print(f"📂 Найдено категорий: {len(categories_found)}")
        print(f"   Категории: {', '.join(sorted(categories_found))}")

        return all_chunks

    def save_for_vector_db(self, output_folder: str = "vector_db_ready",
                           format: str = "json") -> Dict[str, Any]:
        """Сохраняет обработанные документы в формате, готовом для векторной БД."""
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)

        # Подсчёт статистики по категориям
        categories_stats = {}
        files_with_links = 0

        for chunk in self.documents:
            category = chunk['metadata'].get('category', 'unknown')
            categories_stats[category] = categories_stats.get(category, 0) + 1

            if chunk['metadata'].get('has_link'):
                files_with_links += 1

        stats = {
            'total_chunks': len(self.documents),
            'total_characters': sum(len(chunk['text']) for chunk in self.documents),
            'avg_chunk_size': 0,
            'doc_types': {},
            'categories': categories_stats,
            'files_with_links': files_with_links,
            'total_files': len(set(chunk['metadata']['source_file'] for chunk in self.documents))
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

        # Сохраняем в Pickle
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

        # Сохраняем CSV с метаданными файлов
        import csv
        csv_path = output_path / "files_metadata.csv"

        file_metadata = {}
        for chunk in self.documents:
            source_file = chunk['metadata']['source_file']
            if source_file not in file_metadata:
                file_metadata[source_file] = {
                    'filename': source_file,
                    'category': chunk['metadata'].get('category', ''),
                    'doc_type': chunk['metadata'].get('doc_type', ''),
                    'location': chunk['metadata'].get('location', ''),
                    'has_link': chunk['metadata'].get('has_link', False),
                    'original_url': chunk['metadata'].get('original_url', ''),
                    'document_title': chunk['metadata'].get('document_title', ''),
                    'chunks_count': 0,
                    'total_chars': 0
                }
            file_metadata[source_file]['chunks_count'] += 1
            file_metadata[source_file]['total_chars'] += len(chunk['text'])

        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['filename', 'category', 'doc_type', 'location',
                                                   'has_link', 'original_url', 'document_title',
                                                   'chunks_count', 'total_chars'])
            writer.writeheader()
            for data in file_metadata.values():
                writer.writerow(data)

        print(f"✓ CSV с метаданными файлов: {csv_path}")

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
            f.write(f"Средний размер чанка: {stats['avg_chunk_size']} символов\n")
            f.write(f"Всего файлов: {stats['total_files']}\n")
            f.write(f"Файлов со ссылками: {stats['files_with_links']}\n\n")

            f.write("Распределение по типам документов:\n")
            for doc_type, count in sorted(stats['doc_types'].items()):
                f.write(f"  {doc_type}: {count} чанков\n")

            f.write("\nРаспределение по категориям:\n")
            for category, count in sorted(stats['categories'].items()):
                f.write(f"  {category}: {count} чанков\n")

        print(f"✓ Статистика сохранена: {stats_path}")

        return stats

    def create_embeddings_ready_format(self, output_file: str = "embeddings_ready.json"):
        """Создаёт формат, готовый для генерации эмбеддингов."""
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
                'category': chunk['metadata'].get('category', ''),
                'doc_type': chunk['metadata'].get('doc_type', ''),
                'location': chunk['metadata'].get('location', ''),
                'has_link': chunk['metadata'].get('has_link', False),
                'original_url': chunk['metadata'].get('original_url', ''),
                'document_title': chunk['metadata'].get('document_title', ''),
                'chunk_id': chunk['metadata']['chunk_id']
            })

        output_path = Path("embeddings_ready")
        output_path.mkdir(exist_ok=True)

        json_path = output_path / output_file
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(ready_data, f, ensure_ascii=False, indent=2)

        print(f"✓ Готово для эмбеддингов: {json_path}")
        print(f"  Всего записей: {len(ready_data)}")

        return ready_data


def create_sample_embedding_code(output_dir: str = "vector_db_ready"):
    """Создаёт пример кода для генерации эмбеддингов и загрузки в векторную БД."""
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
model = SentenceTransformer('intfloat/multilingual-e5-large')

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

# 5. Тестовый поиск с фильтрацией по категории
query = "правила приема"
results = collection.query(
    query_texts=[query], 
    n_results=5,
    where={"category": "Правила приёма поступающих"}
)

print(f"\\nРезультаты поиска по запросу: '{query}'")
print("="*60)
for i, (doc, metadata, distance) in enumerate(zip(
    results['documents'][0], 
    results['metadatas'][0], 
    results['distances'][0]
)):
    print(f"{i+1}. {metadata.get('category', 'unknown')} - {metadata.get('source_file', 'unknown')}")
    print(f"   {doc[:200]}...\\n")
'''

    code_path = output_path / "example_embedding_code.py"
    with open(code_path, 'w', encoding='utf-8') as f:
        f.write(code_example)

    print(f"✓ Пример кода создан: {code_path}")


def main():
    """Основная функция для обработки документов."""
    print("\n" + "=" * 60)
    print("🔄 ПОДГОТОВКА ДОКУМЕНТОВ ДЛЯ ВЕКТОРНОЙ БД")
    print("=" * 60 + "\n")

    # Создаём процессор документов
    processor = DocumentProcessorForVectorDB(
        chunk_size=1500,  # Размер чанка в символах
        chunk_overlap=200  # Перекрытие между чанками
    )

    # Обрабатываем TXT файлы (рекурсивно с учётом структуры папок)
    chunks = processor.process_txt_files(
        input_folder="downloaded_documents",  # Ваша папка с файлами
        links_file="links"  # Файл со ссылками
    )

    if chunks:
        # Сохраняем в форматах для векторной БД
        stats = processor.save_for_vector_db(
            output_folder="vector_db_ready",
            format="both"
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
        print(f"📁 Всего файлов: {stats['total_files']}")
        print(f"🔗 Файлов со ссылками: {stats['files_with_links']}")

        print(f"\n📂 Результаты сохранены в папке: vector_db_ready/")
        print(f"   - documents_for_vector_db.json (полные данные)")
        print(f"   - documents_for_vector_db.pkl (pickle формат)")
        print(f"   - langchain_documents.json (LangChain формат)")
        print(f"   - embeddings_ready_data.json (готово для эмбеддингов)")
        print(f"   - files_metadata.csv (метаданные файлов)")
        print(f"   - example_embedding_code.py (пример кода)")
        print(f"   - processing_stats.txt (статистика)")

        # Выводим категории
        if stats.get('categories'):
            print("\n📂 Найденные категории документов:")
            for category, count in sorted(stats['categories'].items()):
                if count > 0:
                    print(f"   - {category}: {count} чанков")

    else:
        print("\n❌ Не удалось обработать документы.")
        print("Убедитесь, что:")
        print("1. Папка 'downloaded_documents' существует")
        print("2. Внутри есть вложенные папки с TXT файлами")
        print("3. Файлы имеют расширение .txt")


if __name__ == "__main__":
    main()