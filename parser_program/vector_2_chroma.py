import json
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
import shutil


def create_chromadb_from_json(json_path, db_path="chroma_db", collection_name="documents",
                              force_recreate=False, use_sentence_transformers=True):
    """
    Создает Chroma DB из JSON файла

    Args:
        json_path: путь к JSON файлу с данными
        db_path: путь для сохранения Chroma DB
        collection_name: имя коллекции
        force_recreate: если True, удалит существующую БД и создаст заново
        use_sentence_transformers: использовать Sentence Transformers для эмбеддингов
    """

    # Проверяем существование JSON файла
    json_file = Path(json_path)
    if not json_file.exists():
        print(f"❌ JSON файл {json_path} не найден!")
        return None

    # Загружаем данные из JSON
    print(f"📖 Загрузка данных из {json_path}...")
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        ids = data.get('ids', [])
        documents = data.get('documents', [])
        metadatas = data.get('metadatas', [])

        print(f"✅ Загружено {len(documents)} документов")
        print(f"   - Всего символов: {sum(len(d) for d in documents):,}")

    except Exception as e:
        print(f"❌ Ошибка загрузки JSON: {e}")
        return None

    # Если нужно пересоздать БД
    db_path_obj = Path(db_path)
    if force_recreate and db_path_obj.exists():
        print(f"🗑️  Удаление существующей БД: {db_path}")
        shutil.rmtree(db_path)

    # Создаем клиент Chroma
    print(f"\n🔧 Создание Chroma DB в {db_path}...")
    try:
        client = chromadb.PersistentClient(path=db_path)

        # Выбираем функцию эмбеддингов
        if use_sentence_transformers:
            # Используем Sentence Transformers (лучше для русского языка)
            embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="intfloat/multilingual-e5-small"  # поддерживает русский
            )
            print("   - Используется модель: intfloat/multilingual-e5-small")
        else:
            # Стандартная модель (лучше для английского)
            embedding_fn = embedding_functions.DefaultEmbeddingFunction()
            print("   - Используется стандартная модель")

        # Удаляем коллекцию если существует
        try:
            client.delete_collection(collection_name)
            print(f"   - Удалена существующая коллекция '{collection_name}'")
        except:
            pass

        # Создаем новую коллекцию
        collection = client.create_collection(
            name=collection_name,
            embedding_function=embedding_fn,
            metadata={"hnsw:space": "cosine"}  # используем косинусное расстояние
        )

        print(f"   - Создана коллекция '{collection_name}'")

        # Добавляем документы в БД
        print(f"\n📥 Добавление документов в БД...")

        # Добавляем пакетами по 100 документов для эффективности
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_docs = documents[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]

            collection.add(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_metadatas
            )

            print(f"   - Добавлено {min(i + batch_size, len(documents))} из {len(documents)} документов")

        print(f"\n{'=' * 60}")
        print(f"✅ База данных успешно создана!")
        print(f"📊 Статистика БД:")
        print(f"   - Путь: {db_path}")
        print(f"   - Коллекция: {collection_name}")
        print(f"   - Количество документов: {collection.count()}")
        print(f"   - Размер БД: {get_db_size(db_path)}")
        print(f"{'=' * 60}")

        return client, collection

    except Exception as e:
        print(f"❌ Ошибка создания БД: {e}")
        return None, None


def get_db_size(db_path):
    """Вычисляет размер БД на диске"""
    db_path_obj = Path(db_path)
    if not db_path_obj.exists():
        return "0 KB"

    total_size = 0
    for file in db_path_obj.rglob('*'):
        if file.is_file():
            total_size += file.stat().st_size

    # Форматируем размер
    for unit in ['B', 'KB', 'MB', 'GB']:
        if total_size < 1024.0:
            return f"{total_size:.2f} {unit}"
        total_size /= 1024.0
    return f"{total_size:.2f} TB"


def test_query(collection, query_text, n_results=3):
    """Тестовый поиск в БД"""
    print(f"\n🔍 Тестовый поиск: '{query_text}'")
    print("-" * 50)

    results = collection.query(
        query_texts=[query_text],
        n_results=n_results
    )

    for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
    ), 1):
        print(f"\n{i}. {metadata['document_name']}")
        print(f"   Релевантность: {(1 - distance) * 100:.2f}%")
        print(f"   Ссылка: {metadata.get('pdf_link', 'Нет ссылки')}")
        print(f"   Фрагмент: {doc[:200]}...")


def interactive_search(collection):
    """Интерактивный поиск по БД"""
    print(f"\n{'=' * 60}")
    print("💬 Интерактивный режим поиска")
    print("   Введите ваш вопрос (или 'quit' для выхода, 'stats' для статистики)")
    print(f"{'=' * 60}")

    while True:
        query = input("\n❓ Ваш вопрос: ").strip()

        if query.lower() in ['quit', 'exit', 'q']:
            print("👋 До свидания!")
            break
        elif query.lower() == 'stats':
            print(f"\n📊 Статистика коллекции:")
            print(f"   - Всего документов: {collection.count()}")
            print(f"   - Имена документов:")
            for metadata in collection.get()['metadatas']:
                print(f"     • {metadata['document_name']}")
        elif query:
            test_query(collection, query, n_results=3)


if __name__ == "__main__":
    # Создаем JSON из TXT файлов
    print("=" * 60)
    print("ШАГ 1: СОЗДАНИЕ JSON ФАЙЛА")
    print("=" * 60)

    # Сначала создаем JSON (если еще не создан)
    if not Path("chroma_data.json").exists():
        chroma_data = create_chroma_json("rag_ready_texts", links, "chroma_data.json")
    else:
        print("✅ JSON файл уже существует")
        with open("chroma_data.json", 'r', encoding='utf-8') as f:
            chroma_data = json.load(f)

    print("\n" + "=" * 60)
    print("ШАГ 2: СОЗДАНИЕ CHROMA DB")
    print("=" * 60)

    # Создаем Chroma DB из JSON
    client, collection = create_chromadb_from_json(
        json_path="chroma_data.json",
        db_path="chroma_db",
        collection_name="university_documents",
        force_recreate=True,  # пересоздаем БД заново
        use_sentence_transformers=True  # используем мультиязычную модель
    )

    # Если БД создана, можно выполнить тестовый поиск
    if collection:
        print("\n" + "=" * 60)
        print("ШАГ 3: ТЕСТИРОВАНИЕ ПОИСКА")
        print("=" * 60)

        # Тестовые запросы
        test_queries = [
            "Что написано в уставе университета?",
            "Какие изменения вносились в устав?",
            "Когда был зарегистрирован ЕГРЮЛ?"
        ]

        for query in test_queries:
            test_query(collection, query, n_results=2)

        # Запускаем интерактивный режим
        interactive_search(collection)