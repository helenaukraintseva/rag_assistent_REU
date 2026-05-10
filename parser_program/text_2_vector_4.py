import os
import json
from pathlib import Path


def create_chroma_json(txt_folder_path, links_dict, output_json_path="chroma_data.json"):
    """
    Создает JSON файл с контентом из TXT файлов для Chroma DB

    Args:
        txt_folder_path: путь к папке с TXT файлами
        links_dict: словарь с названиями документов и ссылками на PDF
        output_json_path: путь для сохранения JSON файла
    """

    txt_folder = Path(txt_folder_path)

    if not txt_folder.exists():
        print(f"❌ Папка {txt_folder_path} не существует!")
        return None

    # Получаем список всех TXT файлов
    txt_files = list(txt_folder.glob("*.txt"))

    if not txt_files:
        print(f"❌ В папке {txt_folder_path} нет TXT файлов!")
        return None

    print(f"✅ Найдено TXT файлов: {len(txt_files)}")

    # Данные для Chroma
    documents = []  # тексты документов
    metadatas = []  # метаданные
    ids = []  # уникальные идентификаторы

    total_chars = 0

    # Обрабатываем каждый TXT файл
    for idx, txt_file in enumerate(txt_files, 1):
        # Получаем название файла без расширения
        doc_name = txt_file.stem

        print(f"\n[{idx}/{len(txt_files)}] 📄 Обработка: {doc_name}")

        # Ищем соответствующий документ в словаре ссылок
        link = links_dict.get(doc_name, "")
        if not link:
            print(doc_name)
            print(f"LINK:__{link}__")
            print("FUCK")

        # Читаем содержимое TXT файла
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                print(f"  ⚠️  Предупреждение: Файл {doc_name}.txt пуст")
                continue

            # Создаем ID для документа
            doc_id = doc_name.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('.', '').replace('№',
                                                                                                                   'n')
            doc_id = ''.join(c for c in doc_id if c.isalnum() or c == '_')

            # Добавляем данные
            documents.append(content)
            metadatas.append({
                "source": "pdf",
                "document_name": doc_name,
                "pdf_link": link,
                "file_path": str(txt_file),
                "file_size_kb": round(txt_file.stat().st_size / 1024, 2),
                "char_count": len(content),
                "word_count": len(content.split()),
                "index": idx
            })
            ids.append(doc_id)

            total_chars += len(content)

            print(f"  ✅ Текст загружен")
            print(f"     - Длина: {len(content)} символов")
            print(f"     - Слов: {len(content.split())}")
            print(f"     - Размер: {round(txt_file.stat().st_size / 1024, 2)} KB")
            if link:
                print(f"     - Ссылка: ✓ найдена")
            else:
                print(f"     - Ссылка: ⚠️ отсутствует")

        except Exception as e:
            print(f"  ❌ Ошибка чтения файла: {e}")
            continue

    # Создаем структуру для JSON
    chroma_data = {
        "metadata": {
            "total_documents": len(documents),
            "total_chars": total_chars,
            "created_at": str(Path(output_json_path).stat().st_ctime) if Path(output_json_path).exists() else "new",
            "source_folder": str(txt_folder)
        },
        "ids": ids,
        "documents": documents,
        "metadatas": metadatas
    }

    # Сохраняем в JSON файл
    try:
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(chroma_data, f, ensure_ascii=False, indent=2)

        print(f"\n{'=' * 60}")
        print(f"✅ JSON файл успешно создан: {output_json_path}")
        print(f"📊 Статистика:")
        print(f"   - Всего документов: {len(documents)}")
        print(f"   - Документов со ссылками: {sum(1 for m in metadatas if m['pdf_link'])}")
        print(f"   - Документов без ссылок: {sum(1 for m in metadatas if not m['pdf_link'])}")
        print(f"   - Общий размер текста: {total_chars} символов")
        print(f"   - Размер JSON файла: {round(Path(output_json_path).stat().st_size / 1024, 2)} KB")
        print(f"{'=' * 60}")
        return chroma_data
    except Exception as e:
        print(f"❌ Ошибка сохранения JSON: {e}")
        return None


# Данные из вашего примера
from links_2 import links

if __name__ == "__main__":
    # Создаем JSON с контентом
    chroma_data = create_chroma_json("rag_ready_texts", links, "chroma_data.json")