import json
from api_client import PolzaAIClient


def load_chroma_data(json_path="chroma_data.json"):
    """Загружает данные из chroma_data.json"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Загружено {len(data['documents'])} документов")
        return data
    except FileNotFoundError:
        print(f"❌ Файл {json_path} не найден!")
        return None
    except Exception as e:
        print(f"❌ Ошибка загрузки JSON: {e}")
        return None


def get_text_theme(client, text, max_chars=2000):
    """
    Получает краткое резюме текста через API

    Args:
        client: экземпляр PolzaAIClient
        text: исходный текст
        max_chars: максимальное количество символов для отправки

    Returns:
        str: резюме текста (до 200 символов)
    """
    # Обрезаем текст до max_chars символов
    truncated_text = text[:max_chars]

    # Формируем промпт
    prompt = f"""Напиши краткое резюме этого текста в 100 символов:

{truncated_text}"""

    try:
        response = client.generate_content(prompt, max_tokens=200)
        # Обрезаем результат до 200 символов, если API вернул больше
        if response and len(response) > 200:
            response = response[:200]
        return response
    except Exception as e:
        print(f"  ⚠️ Ошибка при получении темы: {e}")
        return "Тема не определена"


def create_documents_list(chroma_data, client):
    """
    Создает список словарей с документами

    Args:
        chroma_data: данные из chroma_data.json
        client: экземпляр PolzaAIClient

    Returns:
        list: список словарей в формате [{"title": {"text": "...", "link": "...", "theme": "..."}}, ...]
    """
    documents_list = []
    total = len(chroma_data['documents'])

    print(f"\n{'=' * 60}")
    print(f"🔄 Обработка {total} документов...")
    print(f"{'=' * 60}")

    for idx, (doc_id, document, metadata) in enumerate(zip(
            chroma_data['ids'],
            chroma_data['documents'],
            chroma_data['metadatas']
    ), 1):
        print(f"\n[{idx}/{total}] 📄 Обработка: {metadata['document_name']}")

        # Получаем тему (резюме) текста
        print(f"  🤖 Генерация темы через API...")
        theme = get_text_theme(client, document)
        print(f"  ✅ Тема: {theme[:100]}{'...' if len(theme) > 100 else ''}")

        # Создаем словарь для документа
        doc_dict = {
            metadata['document_name']: {
                "text": document[:2000],
                "link": metadata['pdf_link'],
                "theme": theme
            }
        }

        documents_list.append(doc_dict)

        # Статистика по документу
        print(f"  📊 Статистика:")
        print(f"     - Длина текста: {metadata['char_count']} символов")
        print(f"     - Ссылка: {'✓ есть' if metadata['pdf_link'] else '✗ нет'}")

    return documents_list


def save_results(documents_list, output_path="documents_with_themes.json"):
    """Сохраняет результат в JSON файл"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(documents_list, f, ensure_ascii=False, indent=2)

        print(f"\n{'=' * 60}")
        print(f"✅ Результат сохранен в: {output_path}")
        print(f"📊 Итоговая статистика:")
        print(f"   - Всего документов: {len(documents_list)}")
        print(
            f"   - Документов с темой: {sum(1 for d in documents_list for v in d.values() if v['theme'] != 'Тема не определена')}")
        print(f"   - Размер файла: {round(__import__('pathlib').Path(output_path).stat().st_size / 1024, 2)} KB")
        print(f"{'=' * 60}")

        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        return False


def main():
    # Создаем экземпляр клиента API
    print("🔧 Инициализация API клиента...")
    client = PolzaAIClient()

    # Загружаем данные из chroma_data.json
    print("\n📂 Загрузка chroma_data.json...")
    chroma_data = load_chroma_data("chroma_data.json")

    if not chroma_data:
        print("❌ Не удалось загрузить данные. Программа завершена.")
        return

    if len(chroma_data['documents']) == 0:
        print("❌ В файле нет документов для обработки.")
        return

    # Создаем список словарей с темами
    print("\n🔄 Создание списка документов с темами...")
    documents_list = create_documents_list(chroma_data, client)

    # Сохраняем результат
    save_results(documents_list, "documents_with_themes.json")

    # Выводим пример результата
    if documents_list:
        print(f"\n📝 Пример результата (первый документ):")
        print(json.dumps(documents_list[0], ensure_ascii=False, indent=2)[:500] + "...")

    print("\n✨ Программа успешно завершена!")


if __name__ == "__main__":
    main()