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

    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.documents = []

    def clean_text_for_rag(self, text: str) -> str:
        """Очищает текст для использования в RAG."""
        if not text:
            return ""

        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        text = '\n'.join(lines)
        text = text.strip()

        text = re.sub(r'[—–―]', '-', text)
        text = text.replace('\u00a0', ' ')
        text = text.replace('\u200b', '')
        text = text.replace('\ufeff', '')
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

    def extract_metadata(self, filepath: Path, category: str) -> Dict[str, Any]:
        """Извлекает метаданные из файла и категории."""
        filename = filepath.name

        metadata = {
            'source_file': filename,
            'file_path': str(filepath),
            'file_size': filepath.stat().st_size,
            'category': category,
            'document_id': hashlib.md5(str(filepath).encode()).hexdigest(),
            'processed_date': datetime.now().isoformat()
        }

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

        # Извлекаем геолокацию
        locations = ['bryansk', 'volgograd', 'voronezh', 'erevan', 'ivanovo',
                     'krasnodar', 'perm', 'smolensk', 'tula', 'sevastopol',
                     'orenburg', 'pyatigorsk', 'tashkent', 'ulan-bator', 'minsk']

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
            print(f"  Ошибка загрузки: {e}")
            return None

    def process_txt_files(self, input_folder: str = "downloaded_documents") -> List[Dict[str, Any]]:
        """
        Обрабатывает все TXT файлы из вложенных папок.
        Структура: input_folder/категория/*.txt
        """
        input_path = Path(input_folder)

        if not input_path.exists():
            print(f"❌ Папка '{input_folder}' не найдена!")
            return []

        # Находим все подпапки (категории)
        categories = [d for d in input_path.iterdir() if d.is_dir()]

        if not categories:
            print(f"❌ В папке '{input_folder}' нет вложенных папок с категориями!")
            return []

        print(f"📁 Найдено категорий: {len(categories)}")
        print(f"📏 Размер чанка: {self.chunk_size} символов")
        print(f"🔄 Перекрытие: {self.chunk_overlap} символов")
        print("=" * 60)

        all_chunks = []
        total_chunks = 0
        total_files = 0

        for category_path in categories:
            category_name = category_path.name
            print(f"\n📂 Категория: {category_name}")

            # Находим все TXT файлы в текущей категории
            txt_files = list(category_path.glob("*.txt"))
            txt_files = [f for f in txt_files if not f.name.startswith("_")]

            if not txt_files:
                print(f"   ⚠ Нет TXT файлов")
                continue

            print(f"   📄 Найдено файлов: {len(txt_files)}")

            for txt_file in txt_files:
                total_files += 1
                print(f"\n   [{total_files}] Обработка: {txt_file.name}")

                text = self.load_text_file(txt_file)

                if text:
                    cleaned_text = self.clean_text_for_rag(text)
                    metadata = self.extract_metadata(txt_file, category_name)
                    metadata['original_size'] = len(text)
                    metadata['cleaned_size'] = len(cleaned_text)

                    chunks = self.chunk_text(cleaned_text, metadata)

                    if chunks:
                        all_chunks.extend(chunks)
                        total_chunks += len(chunks)
                        print(f"       ✓ Создано чанков: {len(chunks)}")
                        print(f"         Текст: {len(cleaned_text):,} символов")
                    else:
                        print(f"       ⚠ Не удалось создать чанки")
                else:
                    print(f"       ✗ Ошибка загрузки текста")

        self.documents = all_chunks
        print("\n" + "=" * 60)
        print(f"✅ Всего обработано файлов: {total_files}")
        print(f"✅ Всего создано чанков: {total_chunks}")

        return all_chunks

    def save_for_vector_db(self, output_folder: str = "vector_db_ready",
                           format: str = "both") -> Dict[str, Any]:
        """Сохраняет обработанные документы в формате, готовом для векторной БД."""
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)

        # Подсчёт статистики по категориям
        categories_stats = {}
        for chunk in self.documents:
            category = chunk['metadata'].get('category', 'unknown')
            categories_stats[category] = categories_stats.get(category, 0) + 1

        stats = {
            'total_chunks': len(self.documents),
            'total_characters': sum(len(chunk['text']) for chunk in self.documents),
            'avg_chunk_size': 0,
            'doc_types': {},
            'categories': categories_stats,
            'total_files': len(set(chunk['metadata']['source_file'] for chunk in self.documents))
        }

        if self.documents:
            stats['avg_chunk_size'] = stats['total_characters'] // len(self.documents)

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
        langchain_data = [
            {'page_content': chunk['text'], 'metadata': chunk['metadata']}
            for chunk in self.documents
        ]
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
            f.write(f"Средний размер чанка: {stats['avg_chunk_size']} символов\n")
            f.write(f"Всего файлов: {stats['total_files']}\n\n")

            f.write("Распределение по типам документов:\n")
            for doc_type, count in sorted(stats['doc_types'].items()):
                f.write(f"  {doc_type}: {count} чанков\n")

            f.write("\nРаспределение по категориям:\n")
            for category, count in sorted(stats['categories'].items()):
                f.write(f"  {category}: {count} чанков\n")

        print(f"✓ Статистика сохранена: {stats_path}")

        return stats

    def create_embeddings_ready_format(self, output_file: str = "embeddings_ready_data.json"):
        """Создаёт формат, готовый для генерации эмбеддингов."""
        if not self.documents:
            print("❌ Нет обработанных документов")
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


def main():
    """Основная функция для обработки документов."""
    print("\n" + "=" * 60)
    print("🔄 ПОДГОТОВКА ДОКУМЕНТОВ ДЛЯ ВЕКТОРНОЙ БД")
    print("=" * 60 + "\n")

    processor = DocumentProcessorForVectorDB(
        chunk_size=1500,
        chunk_overlap=200
    )

    # Обрабатываем TXT файлы из структуры downloaded_documents/категория/*.txt
    chunks = processor.process_txt_files(input_folder="downloaded_documents")

    if chunks:
        stats = processor.save_for_vector_db(
            output_folder="vector_db_ready",
            format="both"
        )

        embedding_ready = processor.create_embeddings_ready_format(
            output_file="embeddings_ready_data.json"
        )

        print("\n" + "=" * 60)
        print("📊 ФИНАЛЬНАЯ СТАТИСТИКА")
        print("=" * 60)
        print(f"✅ Всего чанков: {stats['total_chunks']}")
        print(f"📝 Всего символов: {stats['total_characters']:,}")
        print(f"📏 Средний размер чанка: {stats['avg_chunk_size']} символов")
        print(f"📁 Всего файлов: {stats['total_files']}")

        print(f"\n📂 Результаты сохранены в папке: vector_db_ready/")
        print(f"   - documents_for_vector_db.json")
        print(f"   - documents_for_vector_db.pkl")
        print(f"   - langchain_documents.json")
        print(f"   - embeddings_ready_data.json")
        print(f"   - processing_stats.txt")

        if stats.get('categories'):
            print("\n📂 Найденные категории:")
            for category, count in sorted(stats['categories'].items()):
                print(f"   - {category}: {count} чанков")

    else:
        print("\n❌ Не удалось обработать документы.")
        print("Проверьте структуру папок:")
        print("downloaded_documents/")
        print("├── Устав образовательной организации/")
        print("│   └── *.txt")
        print("├── Правила приёма поступающих/")
        print("│   └── *.txt")
        print("└── ...")


if __name__ == "__main__":
    main()