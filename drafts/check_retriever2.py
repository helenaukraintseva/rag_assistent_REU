#!/usr/bin/env python3
"""
Тест исправленного ретривера.
"""

from retriever import get_retriever


def test_retriever():
    """Тестирование ретривера"""
    print("Тестирование ретривера...")

    # Тест 1: С явным указанием collection_name
    print("\n1. Тест с collection_name='documents':")
    try:
        retriever1 = get_retriever(
            persist_directory="C:\\Projects\\rag_system\\rag_vector_db\\outputs\\chroma_db",
            collection_name="documents",
            use_chromadb=True,
            force_new=True
        )
        print("   ✅ Успешно")

        # Проверка здоровья
        health = retriever1.health_check()
        print(f"   Health check: {health}")

        # Тестовый поиск
        results = retriever1.search("расписание", k=2)
        print(f"   Найдено результатов: {len(results)}")

    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

    # Тест 2: Без указания collection_name (должен использовать значение по умолчанию)
    print("\n2. Тест без указания collection_name:")
    try:
        retriever2 = get_retriever(
            persist_directory="C:\\Projects\\rag_system\\rag_vector_db\\outputs\\chroma_db",
            use_chromadb=True,
            force_new=True
        )
        print("   ✅ Успешно")

        # Проверка здоровья
        health = retriever2.health_check()
        print(f"   Health check: {health}")

    except Exception as e:
        print(f"   ❌ Ошибка: {e}")


if __name__ == "__main__":
    test_retriever()