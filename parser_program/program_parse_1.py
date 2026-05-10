import requests
from pathlib import Path
import re
from urllib.parse import unquote


def sanitize_filename(filename):
    """
    Очищает имя файла от недопустимых символов.
    """
    # Удаляем или заменяем недопустимые символы для имен файлов
    invalid_chars = r'[<>:"/\\|?*]'
    filename = re.sub(invalid_chars, '_', filename)
    # Ограничиваем длину имени файла
    if len(filename) > 200:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:195] + ('.' + ext if ext else '')
    return filename


def extract_filename_from_url(url, fallback_name):
    """
    Извлекает имя файла из URL или использует запасное имя.
    """
    # Декодируем URL
    decoded_url = unquote(url)
    # Пробуем взять имя из URL
    url_filename = Path(decoded_url).name
    if url_filename and '.' in url_filename:
        return sanitize_filename(url_filename)
    # Если не получилось, используем запасное имя
    return sanitize_filename(f"{fallback_name}.pdf")


def download_pdf(url, output_path):
    """
    Скачивает PDF-файл по указанной ссылке.

    Args:
        url (str): URL файла для скачивания.
        output_path (Path): Путь для сохранения файла.

    Returns:
        bool: True если скачивание успешно, False в противном случае.
    """
    try:
        # Выполняем GET-запрос с потоковой загрузкой
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        # Проверяем, что это PDF (по Content-Type)
        content_type = response.headers.get('Content-Type', '')
        if 'pdf' not in content_type.lower():
            print(f"  ⚠ Внимание: {content_type} (возможно, не PDF)")

        # Сохраняем файл
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Проверяем размер файла
        file_size = output_path.stat().st_size
        if file_size < 1024:  # Меньше 1KB - возможно ошибка
            print(f"  ⚠ Файл очень маленький ({file_size} байт), возможно ошибка")

        return True

    except requests.exceptions.RequestException as e:
        print(f"  ✗ Ошибка при скачивании: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Непредвиденная ошибка: {e}")
        return False


def download_category(category_name, links_dict, base_download_dir):
    """
    Скачивает все документы из указанной категории.

    Args:
        category_name (str): Название категории (будет использовано как имя папки).
        links_dict (dict): Словарь с названиями документов и URL.
        base_download_dir (Path): Базовая директория для скачиваний.

    Returns:
        tuple: (успешно_скачано, всего_документов)
    """
    # Создаём папку для категории
    category_folder = base_download_dir / sanitize_filename(category_name)
    category_folder.mkdir(parents=True, exist_ok=True)

    successful = 0
    total = 0

    # Считаем количество непустых ссылок
    for doc_name, url in links_dict.items():
        if url and url.strip():  # Пропускаем пустые ссылки
            total += 1

    if total == 0:
        print(f"\n📁 {category_name}: нет ссылок для скачивания")
        return 0, 0

    print(f"\n{'=' * 60}")
    print(f"📁 Категория: {category_name}")
    print(f"📂 Сохраняется в: {category_folder}")
    print(f"📄 Всего документов: {total}")
    print('-' * 60)

    for doc_name, url in links_dict.items():
        if not url or not url.strip():
            continue

        # Очищаем имя документа для использования как имя файла
        safe_doc_name = sanitize_filename(doc_name)

        # Если в имени документа есть расширение .pdf, не добавляем повторно
        if safe_doc_name.lower().endswith('.pdf'):
            filename = safe_doc_name
        else:
            filename = f"{safe_doc_name}.pdf"

        filepath = category_folder / filename

        # Если файл уже существует, пропускаем
        if filepath.exists():
            print(f"  ⏭ Пропуск (уже существует): {filename}")
            successful += 1
            continue

        print(f"  ⬇ Скачивание: {doc_name}")
        print(f"    URL: {url[:80]}..." if len(url) > 80 else f"    URL: {url}")

        if download_pdf(url, filepath):
            successful += 1
            print(f"    ✓ Сохранён: {filepath.name}")
        else:
            print(f"    ✗ Ошибка при скачивании")

        print()  # Пустая строка для разделения

    return successful, total


def download_all_documents(links_dict, base_download_dir="downloaded_documents"):
    """
    Скачивает все документы из структурированного словаря ссылок.

    Args:
        links_dict (dict): Словарь с категориями и ссылками.
        base_download_dir (str): Базовая директория для скачиваний.

    Returns:
        dict: Статистика по категориям.
    """
    base_path = Path(base_download_dir)
    base_path.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("🚀 НАЧАЛО СКАЧИВАНИЯ ДОКУМЕНТОВ")
    print(f"📁 Базовая директория: {base_path.absolute()}")
    print("=" * 60)

    stats = {}
    total_successful = 0
    total_documents = 0

    for category_name, category_links in links_dict.items():
        # Пропускаем пустые категории
        if not category_links:
            print(f"\n⚠ Пропуск пустой категории: {category_name}")
            continue

        # Пропускаем категории без реальных ссылок
        has_links = any(url and url.strip() for url in category_links.values())
        if not has_links:
            print(f"\n⚠ Пропуск категории без ссылок: {category_name}")
            continue

        success, total = download_category(category_name, category_links, base_path)
        stats[category_name] = {'success': success, 'total': total}
        total_successful += success
        total_documents += total

    return stats, total_successful, total_documents


def print_summary(stats, total_successful, total_documents):
    """
    Выводит итоговую статистику скачивания.
    """
    print("\n" + "=" * 60)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 60)

    for category, data in stats.items():
        status = "✓" if data['success'] == data['total'] else "⚠"
        print(f"{status} {category}: {data['success']}/{data['total']}")

    print("-" * 60)
    print(f"📈 Всего скачано: {total_successful} из {total_documents} документов")

    if total_successful == total_documents:
        print("✅ Все документы успешно скачаны!")
    elif total_successful > 0:
        print(f"⚠ Частичный успех. {total_documents - total_successful} документов не удалось скачать.")
    else:
        print("❌ Не удалось скачать ни одного документа. Проверьте подключение к интернету.")

    print("=" * 60)


# Импортируем ссылки из файла links.py
try:
    from links import links
except ImportError:
    print("Ошибка: файл links.py не найден!")
    print("Убедитесь, что файл links.py находится в той же директории.")
    exit(1)

if __name__ == "__main__":
    # Запускаем скачивание
    stats, total_successful, total_documents = download_all_documents(links)

    # Выводим итоги
    print_summary(stats, total_successful, total_documents)

    # Дополнительно: создаём файл с отчётом
    report_path = Path("download_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("ОТЧЁТ О СКАЧИВАНИИ ДОКУМЕНТОВ\n")
        f.write("=" * 50 + "\n\n")
        for category, data in stats.items():
            f.write(f"{category}: {data['success']}/{data['total']}\n")
        f.write(f"\nВсего: {total_successful} из {total_documents}\n")

    print(f"\n📄 Отчёт сохранён в: {report_path}")