from retriever import get_retriever

# Получить экземпляр ретривера
retriever = get_retriever()

# Поиск релевантных документов
results = retriever.search("Какое расписание на понедельник?", k=3)

# Использовать результаты для RAG
for result in results:
    print(f"Источник: {result.source}")
    print(f"Текст: {result.text[:200]}...")
    print(f"Сходство: {result.score:.3f}")
    print()