#!/usr/bin/env python3
"""
Тестирование работы ChromaDB.
"""

from rag_vector_db.chroma_manager import ChromaDBManager, get_embedding_function


def test_chromadb():
    """Тестовая функция"""

    # 1. Инициализация
    embed_function = get_embedding_function()
    chroma = ChromaDBManager(
        persist_directory="test_chroma_db",
        collection_name="test_docs",
        embedding_function=embed_function
    )

    # 2. Создание коллекции
    chroma.create_collection()

    # 3. Добавление тестовых документов
    documents = [
        "Расписание занятий на понедельник: 9:00 Математика",
        "Контакты деканата: кабинет 101, тел. 123-45-67",
        "Правила обучения: посещаемость обязательна"
    ]

    metadatas = [
        {"source": "schedule.txt", "type": "schedule"},
        {"source": "contacts.txt", "type": "contacts"},
        {"source": "rules.txt", "type": "rules"}
    ]

    chroma.add_documents(documents, metadatas)

    # 4. Поиск
    results = chroma.search(["расписание занятий"], n_results=2)

    print("Результаты поиска:")
    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        print(f"- {doc[:50]}... (источник: {meta['source']})")

    # 5. Информация
    info = chroma.get_collection_info()
    print(f"\nИнформация о коллекции: {info}")

    # 6. Очистка
    chroma.clear_collection()


if __name__ == "__main__":
    test_chromadb()