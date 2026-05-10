# test_rag_integration.py
import requests
import json


def test_rag_integration():
    """Тестирование полной RAG интеграции"""

    print("🔍 Тестирование RAG системы с LLM")
    print("=" * 50)

    # Тестовые вопросы
    test_questions = [
        "Какое расписание занятий?",
        "Как связаться с деканатом?",
        "Какие правила обучения?",
        "Что такое стипендия и как её получить?",
        "Как взять академический отпуск?"
    ]

    for question in test_questions:
        print(f"\n📝 Вопрос: {question}")

        try:
            response = requests.post(
                "http://localhost:5000/api/ask",
                json={
                    "question": question,
                    "k": 3,
                    "threshold": 0.3,
                    "use_llm": True
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print(f"✅ Успех")
                    print(f"   Документов найдено: {data.get('documents_count', 0)}")
                    print(f"   Время: {data.get('total_time', 0):.2f}с")
                    print(f"   Ответ: {data.get('answer', '')[:100]}...")
                else:
                    print(f"❌ Ошибка: {data.get('error', 'Unknown error')}")
            else:
                print(f"❌ HTTP ошибка: {response.status_code}")

        except Exception as e:
            print(f"❌ Ошибка соединения: {e}")

    print("\n" + "=" * 50)
    print("✅ Тестирование завершено")


if __name__ == "__main__":
    test_rag_integration()