import requests
from pathlib import Path
import re
from urllib.parse import unquote
import time
import random


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


def file_exists(filepath):
    """
    Проверяет, существует ли файл и имеет ли он ненулевой размер.

    Args:
        filepath (Path): Путь к файлу.

    Returns:
        bool: True если файл существует и не пустой.
    """
    if filepath.exists():
        if filepath.stat().st_size > 0:
            return True
        else:
            # Если файл пустой, удаляем его
            filepath.unlink()
            print(f"  🗑 Удалён пустой файл: {filepath.name}")
    return False


def download_pdf(url, output_path, max_retries=3):
    """
    Скачивает PDF-файл по указанной ссылке с повторными попытками.

    Args:
        url (str): URL файла для скачивания.
        output_path (Path): Путь для сохранения файла.
        max_retries (int): Максимальное количество попыток при ошибке.

    Returns:
        bool: True если скачивание успешно, False в противном случае.
    """
    for attempt in range(max_retries):
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
                if attempt < max_retries - 1:
                    print(f"  🔄 Повторная попытка ({attempt + 2}/{max_retries})...")
                    time.sleep(2)
                    continue

            return True

        except requests.exceptions.RequestException as e:
            print(f"  ✗ Ошибка при скачивании (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"  🔄 Повтор через 3 секунды...")
                time.sleep(3)
        except Exception as e:
            print(f"  ✗ Непредвиденная ошибка: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)

    return False


def download_category(category_name, links_dict, base_download_dir, delay_range=(3, 5)):
    """
    Скачивает все документы из указанной категории с проверкой существования файлов.

    Args:
        category_name (str): Название категории (будет использовано как имя папки).
        links_dict (dict): Словарь с названиями документов и URL.
        base_download_dir (Path): Базовая директория для скачиваний.
        delay_range (tuple): Диапазон задержки между скачиваниями (мин, макс) в секундах.

    Returns:
        tuple: (успешно_скачано, всего_документов, пропущено)
    """
    # Создаём папку для категории
    category_folder = base_download_dir / sanitize_filename(category_name)
    category_folder.mkdir(parents=True, exist_ok=True)

    successful = 0
    skipped = 0
    total = 0

    # Считаем количество непустых ссылок
    for doc_name, url in links_dict.items():
        if url and url.strip():  # Пропускаем пустые ссылки
            total += 1

    if total == 0:
        print(f"\n📁 {category_name}: нет ссылок для скачивания")
        return 0, 0, 0

    print(f"\n{'=' * 60}")
    print(f"📁 Категория: {category_name}")
    print(f"📂 Сохраняется в: {category_folder}")
    print(f"📄 Всего документов: {total}")
    print('-' * 60)

    doc_number = 0
    for doc_name, url in links_dict.items():
        if not url or not url.strip():
            continue

        doc_number += 1

        # Очищаем имя документа для использования как имя файла
        safe_doc_name = sanitize_filename(doc_name)

        # Если в имени документа есть расширение .pdf, не добавляем повторно
        if safe_doc_name.lower().endswith('.pdf'):
            filename = safe_doc_name
        else:
            filename = f"{safe_doc_name}.pdf"

        filepath = category_folder / filename

        # Проверяем, существует ли файл уже
        if file_exists(filepath):
            print(f"  [{doc_number}/{total}] ⏭ Пропуск (уже существует): {filename}")
            skipped += 1
            continue

        print(f"  [{doc_number}/{total}] ⬇ Скачивание: {doc_name}")
        print(f"    URL: {url[:80]}..." if len(url) > 80 else f"    URL: {url}")

        if download_pdf(url, filepath):
            successful += 1
            print(f"    ✓ Сохранён: {filepath.name}")
        else:
            print(f"    ✗ Ошибка при скачивании после нескольких попыток")

        # Задержка перед следующим скачиванием (кроме последнего)
        if doc_number < total:
            delay = random.uniform(*delay_range)
            print(f"    ⏳ Пауза {delay:.1f} секунд...")
            time.sleep(delay)

        print()  # Пустая строка для разделения

    return successful, total, skipped


def download_all_documents(links_dict, base_download_dir="downloaded_documents", delay_range=(3, 5)):
    """
    Скачивает все документы из структурированного словаря ссылок.

    Args:
        links_dict (dict): Словарь с категориями и ссылками.
        base_download_dir (str): Базовая директория для скачиваний.
        delay_range (tuple): Диапазон задержки между скачиваниями (мин, макс) в секундах.

    Returns:
        dict: Статистика по категориям.
    """
    base_path = Path(base_download_dir)
    base_path.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("🚀 НАЧАЛО СКАЧИВАНИЯ ДОКУМЕНТОВ")
    print(f"📁 Базовая директория: {base_path.absolute()}")
    print(f"⏱  Задержка между скачиваниями: {delay_range[0]}-{delay_range[1]} секунд")
    print("=" * 60)

    stats = {}
    total_successful = 0
    total_skipped = 0
    total_documents = 0

    category_number = 0
    total_categories = len([cat for cat in links_dict.keys() if links_dict.get(cat)])

    for category_name, category_links in links_dict.items():
        # Пропускаем пустые категории
        if not category_links:
            print(f"\n⚠ Пропуск пустой категории: {category_name}")
            continue

        # Проверяем, есть ли реальные ссылки
        has_links = any(url and url.strip() for url in category_links.values())
        if not has_links:
            print(f"\n⚠ Пропуск категории без ссылок: {category_name}")
            continue

        category_number += 1
        print(f"\n{'🔄' * 30}")
        print(f"📂 Категория {category_number}/{total_categories}")

        success, total, skipped = download_category(category_name, category_links, base_path, delay_range)
        stats[category_name] = {'success': success, 'total': total, 'skipped': skipped}
        total_successful += success
        total_skipped += skipped
        total_documents += total

        # Задержка между категориями
        if category_number < total_categories:
            delay_between_categories = random.uniform(5, 8)
            print(f"⏳ Пауза между категориями {delay_between_categories:.1f} секунд...")
            time.sleep(delay_between_categories)

    return stats, total_successful, total_skipped, total_documents


def print_summary(stats, total_successful, total_skipped, total_documents):
    """
    Выводит итоговую статистику скачивания.
    """
    print("\n" + "=" * 60)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 60)

    for category, data in stats.items():
        downloaded = data['success']
        skipped = data['skipped']
        total = data['total']
        status = "✓" if downloaded + skipped == total else "⚠"
        print(f"{status} {category}: скачано {downloaded}, пропущено {skipped}, всего {total}")

    print("-" * 60)
    print(f"📈 Всего:")
    print(f"   ✓ Скачано новых файлов: {total_successful}")
    print(f"   ⏭ Пропущено (уже существовали): {total_skipped}")
    print(f"   📄 Всего документов: {total_documents}")

    if total_successful + total_skipped == total_documents:
        print("✅ Все документы успешно обработаны!")
    elif total_successful > 0:
        print(f"⚠ Частичный успех. {total_documents - total_successful - total_skipped} документов не удалось скачать.")
    else:
        print("❌ Не удалось скачать ни одного документа. Проверьте подключение к интернету.")

    print("=" * 60)


def check_missing_files(links_dict, base_download_dir="downloaded_documents"):
    """
    Проверяет, какие файлы еще не скачаны.

    Args:
        links_dict (dict): Словарь с категориями и ссылками.
        base_download_dir (str): Базовая директория для скачиваний.

    Returns:
        dict: Словарь с пропущенными файлами.
    """
    base_path = Path(base_download_dir)
    missing = {}

    print("\n" + "=" * 60)
    print("🔍 ПРОВЕРКА ОТСУТСТВУЮЩИХ ФАЙЛОВ")
    print("=" * 60)

    for category_name, category_links in links_dict.items():
        if not category_links:
            continue

        category_folder = base_path / sanitize_filename(category_name)
        missing_files = []

        for doc_name, url in category_links.items():
            if not url or not url.strip():
                continue

            safe_doc_name = sanitize_filename(doc_name)
            if safe_doc_name.lower().endswith('.pdf'):
                filename = safe_doc_name
            else:
                filename = f"{safe_doc_name}.pdf"

            filepath = category_folder / filename

            if not file_exists(filepath):
                missing_files.append((doc_name, url))

        if missing_files:
            missing[category_name] = missing_files

    if missing:
        print("\n❌ Отсутствуют файлы в следующих категориях:")
        for category, files in missing.items():
            print(f"\n  📁 {category}:")
            for doc_name, url in files:
                print(f"    - {doc_name}")
    else:
        print("\n✅ Все файлы присутствуют!")

    return missing


# Импортируем ссылки из файла links.py
try:
    from links import links
except ImportError:
    print("Ошибка: файл links.py не найден!")
    print("Убедитесь, что файл links.py находится в той же директории.")
    exit(1)

if __name__ == "__main__":
    import argparse

    # Создаём парсер аргументов командной строки
    parser = argparse.ArgumentParser(description='Скачивание документов с сайта РЭУ им. Плеханова')
    parser.add_argument('--check-only', action='store_true',
                        help='Только проверить отсутствующие файлы, не скачивать')
    parser.add_argument('--delay-min', type=float, default=3.0,
                        help='Минимальная задержка между скачиваниями (секунды)')
    parser.add_argument('--delay-max', type=float, default=5.0,
                        help='Максимальная задержка между скачиваниями (секунды)')
    parser.add_argument('--output-dir', type=str, default='downloaded_documents',
                        help='Директория для сохранения файлов')

    args = parser.parse_args()

    if args.check_only:
        # Только проверяем отсутствующие файлы
        missing = check_missing_files(links, args.output_dir)
        if missing:
            print("\n💡 Запустите программу без параметра --check-only для скачивания отсутствующих файлов.")
    else:
        # Запускаем скачивание с указанными параметрами
        stats, total_successful, total_skipped, total_documents = download_all_documents(
            links,
            base_download_dir=args.output_dir,
            delay_range=(args.delay_min, args.delay_max)
        )

        # Выводим итоги
        print_summary(stats, total_successful, total_skipped, total_documents)

        # Создаём файл с отчётом
        report_path = Path(args.output_dir) / "download_report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("ОТЧЁТ О СКАЧИВАНИИ ДОКУМЕНТОВ\n")
            f.write("=" * 50 + "\n\n")
            for category, data in stats.items():
                f.write(f"{category}:\n")
                f.write(f"  - Скачано: {data['success']}\n")
                f.write(f"  - Пропущено (уже были): {data['skipped']}\n")
                f.write(f"  - Всего: {data['total']}\n\n")
            f.write(f"\nИТОГО:\n")
            f.write(f"  Скачано новых файлов: {total_successful}\n")
            f.write(f"  Пропущено (уже существовали): {total_skipped}\n")
            f.write(f"  Всего документов: {total_documents}\n")

        print(f"\n📄 Отчёт сохранён в: {report_path}")

        # Проверяем, какие файлы могли остаться
        missing = check_missing_files(links, args.output_dir)