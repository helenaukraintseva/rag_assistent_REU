import os
import re
import PyPDF2
from pathlib import Path
import sys


def clean_text_for_rag(text):
    """
    Очищает текст от лишних символов и нормализует пробелы для использования в RAG.
    """
    if not text:
        return ""

    # Удаляем управляющие символы, кроме перевода строки и табуляции
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # Заменяем множественные пробелы на один
    text = re.sub(r' +', ' ', text)

    # Заменяем множественные переводы строк на два максимум
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

    # Удаляем пробелы в начале и конце строк
    lines = text.split('\n')
    lines = [line.strip() for line in lines]
    text = '\n'.join(lines)

    # Удаляем пустые строки в начале и конце
    text = text.strip()

    # Нормализуем дефисы и тире
    text = re.sub(r'[—–―]', '-', text)

    # Удаляем неразрывные пробелы и другие спецсимволы
    text = text.replace('\u00a0', ' ')  # неразрывный пробел
    text = text.replace('\u200b', '')  # zero-width space
    text = text.replace('\u200c', '')  # zero-width non-joiner
    text = text.replace('\u200d', '')  # zero-width joiner
    text = text.replace('\ufeff', '')  # BOM

    # Удаляем повторяющиеся знаки препинания
    text = re.sub(r'\.{3,}', '...', text)  # многоточие
    text = re.sub(r'[,]{2,}', ',', text)
    text = re.sub(r'[!]{2,}', '!', text)
    text = re.sub(r'[?]{2,}', '?', text)

    # Нормализуем кавычки (опционально)
    text = re.sub(r'[«»″„“]', '"', text)
    text = re.sub(r'[‘’‛]', "'", text)

    # Удаляем пробелы перед знаками препинания
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)

    # Добавляем пробел после знаков препинания (если нет пробела)
    text = re.sub(r'([.,!?;:])([^\s\d])', r'\1 \2', text)

    return text


def remove_noise_lines(text, min_line_length=10):
    """
    Удаляет строки, которые вероятно являются шумом (слишком короткие,
    состоящие только из спецсимволов и т.д.)
    """
    if not text:
        return ""

    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        # Удаляем строки, которые состоят только из цифр, точек и дефисов (нумерация страниц)
        if re.match(r'^[\d\s\.\-–—]+$', line.strip()):
            continue

        # Удаляем строки, которые слишком короткие и не содержат букв
        if len(line.strip()) < min_line_length and not re.search(r'[а-яА-Яa-zA-Z]', line):
            continue

        # Удаляем строки с большим количеством спецсимволов
        if line.strip():
            spec_chars_ratio = len(re.findall(r'[^\w\s\.\,\!\?\-\'\"\(\)]', line)) / max(len(line), 1)
            if spec_chars_ratio > 0.5:
                continue

        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def extract_text_from_pdf(pdf_path, clean=True):
    """
    Извлекает текст из PDF-файла с очисткой.
    """
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)

            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    if clean:
                        page_text = clean_text_for_rag(page_text)
                    text += page_text + "\n"
                else:
                    # Пробуем альтернативный метод извлечения
                    try:
                        page_text = page.extract_text(extraction_mode="layout")
                        if page_text:
                            if clean:
                                page_text = clean_text_for_rag(page_text)
                            text += page_text + "\n"
                    except:
                        pass

        if text.strip():
            # Финальная очистка
            if clean:
                text = clean_text_for_rag(text)
                text = remove_noise_lines(text)
            return text
        else:
            return None

    except Exception as e:
        print(f"  Ошибка при чтении {pdf_path}: {str(e)}")
        return None


def save_text_to_file(text, output_path):
    """Сохраняет текст в UTF-8 формате."""
    try:
        # Создаём родительские папки, если их нет
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        return True
    except Exception as e:
        print(f"  Ошибка при сохранении {output_path}: {str(e)}")
        return False


def get_text_statistics(text):
    """Возвращает статистику по тексту."""
    if not text:
        return {"chars": 0, "words": 0, "lines": 0, "pages_approx": 0}

    lines = text.split('\n')
    non_empty_lines = [l for l in lines if l.strip()]
    words = re.findall(r'[\wа-яА-Я]+', text)

    return {
        "chars": len(text),
        "chars_no_spaces": len(text.replace(' ', '').replace('\n', '')),
        "words": len(words),
        "lines": len(lines),
        "non_empty_lines": len(non_empty_lines),
        "pages_approx": max(1, len(non_empty_lines) // 40)
    }


def convert_pdfs_to_txt(input_folder="downloaded_documents", output_folder="txt_documents", clean=True,
                        min_line_length=10):
    """
    Конвертирует все PDF-файлы из папки и её подпапок в текстовые файлы с сохранением структуры.

    Структура:
    input_folder/
    ├── категория1/
    │   ├── файл1.pdf
    │   └── файл2.pdf
    └── категория2/
        ├── файл3.pdf
        └── файл4.pdf

    Сохраняется в:
    output_folder/
    ├── категория1/
    │   ├── файл1.txt
    │   └── файл2.txt
    └── категория2/
        ├── файл3.txt
        └── файл4.txt
    """
    input_path = Path(input_folder)
    output_path = Path(output_folder)

    if not input_path.exists():
        print(f"❌ Папка '{input_folder}' не найдена!")
        return

    # Находим все подпапки (категории)
    categories = [d for d in input_path.iterdir() if d.is_dir()]

    if not categories:
        print(f"❌ В папке '{input_folder}' нет вложенных папок с категориями!")
        return

    print(f"📁 Найдено категорий: {len(categories)}")
    print(f"📂 Входная папка: {input_folder}")
    print(f"📂 Выходная папка: {output_folder}")
    print(f"🧹 Очистка текста: {'Включена' if clean else 'Выключена'}")
    print("=" * 60)

    # Статистика
    statistics_log = []
    successful = 0
    failed = 0
    total_pdfs = 0

    for category_path in categories:
        category_name = category_path.name
        print(f"\n📂 Категория: {category_name}")

        # Находим все PDF-файлы в текущей категории
        pdf_files = list(category_path.glob("*.pdf"))

        if not pdf_files:
            print(f"   ⚠ Нет PDF файлов")
            continue

        print(f"   📄 Найдено PDF: {len(pdf_files)}")

        # Создаём соответствующую папку в выходной директории
        category_output_path = output_path / category_name
        category_output_path.mkdir(parents=True, exist_ok=True)

        for pdf_path in pdf_files:
            total_pdfs += 1
            print(f"\n   [{total_pdfs}] Обработка: {pdf_path.name}")

            # Извлекаем текст из PDF
            text = extract_text_from_pdf(pdf_path, clean=clean)

            if text:
                # Применяем дополнительную очистку строк
                if clean:
                    text = remove_noise_lines(text, min_line_length=min_line_length)

                # Создаем имя для выходного файла
                output_filename = pdf_path.stem + ".txt"
                output_filepath = category_output_path / output_filename

                # Сохраняем текст
                if save_text_to_file(text, output_filepath):
                    stats = get_text_statistics(text)
                    statistics_log.append({
                        "category": category_name,
                        "file": pdf_path.name,
                        "output": output_filename,
                        "stats": stats
                    })

                    print(f"       ✓ Сохранён: {output_filepath}")
                    print(
                        f"         Символов: {stats['chars']:,} | Слов: {stats['words']:,} | Строк: {stats['non_empty_lines']}")
                    successful += 1
                else:
                    print(f"       ✗ Ошибка при сохранении")
                    failed += 1
            else:
                print(f"       ✗ Не удалось извлечь текст")
                failed += 1

    # Сохраняем общую статистику
    print("\n" + "=" * 60)
    if statistics_log:
        stats_path = output_path / "_conversion_stats.txt"
        with open(stats_path, 'w', encoding='utf-8') as f:
            f.write("СТАТИСТИКА КОНВЕРТАЦИИ PDF -> TXT\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Дата конвертации: {Path(__file__).stat().st_ctime}\n")
            f.write(f"Входная папка: {input_folder}\n")
            f.write(f"Выходная папка: {output_folder}\n\n")

            total_chars = 0
            total_words = 0
            current_category = ""

            for log in statistics_log:
                if log["category"] != current_category:
                    current_category = log["category"]
                    f.write(f"\n{'=' * 50}\n")
                    f.write(f"Категория: {current_category}\n")
                    f.write(f"{'=' * 50}\n")

                f.write(f"\nФайл: {log['file']}\n")
                f.write(f"  -> {log['output']}\n")
                f.write(f"  Символов: {log['stats']['chars']:,}\n")
                f.write(f"  Слов: {log['stats']['words']:,}\n")
                f.write(f"  Строк: {log['stats']['non_empty_lines']}\n")
                f.write(f"  Примерно страниц: {log['stats']['pages_approx']}\n")

                total_chars += log['stats']['chars']
                total_words += log['stats']['words']

            f.write("\n" + "=" * 60 + "\n")
            f.write(f"ВСЕГО ПО ВСЕМ КАТЕГОРИЯМ:\n")
            f.write(f"  Файлов обработано: {successful}\n")
            f.write(f"  Символов: {total_chars:,}\n")
            f.write(f"  Слов: {total_words:,}\n")

        print(f"✓ Статистика сохранена в: {stats_path}")

    print("=" * 60)
    print(f"📊 ИТОГИ КОНВЕРТАЦИИ:")
    print(f"   ✅ Успешно: {successful}")
    print(f"   ❌ Ошибок: {failed}")
    print(f"   📁 Всего PDF: {total_pdfs}")
    print(f"\n📂 TXT файлы сохранены в папке: {output_folder}")
    print(f"   Структура папок сохранена!")


def convert_single_pdf(pdf_path, output_path=None, clean=True, preserve_structure=True,
                       base_input_folder="downloaded_documents", base_output_folder="txt_documents"):
    """
    Конвертирует один PDF-файл в текстовый с очисткой, сохраняя структуру.

    Args:
        pdf_path (str): Путь к PDF-файлу
        output_path (str, optional): Путь для сохранения TXT-файла
        clean (bool): Очищать ли текст от лишних символов
        preserve_structure (bool): Сохранять ли структуру папок
        base_input_folder (str): Базовая входная папка
        base_output_folder (str): Базовая выходная папка
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        print(f"Файл не найден: {pdf_path}")
        return False

    if output_path is None and preserve_structure:
        # Сохраняем структуру относительно base_input_folder
        try:
            rel_path = pdf_path.relative_to(base_input_folder)
            output_path = Path(base_output_folder) / rel_path.with_suffix('.txt')
        except ValueError:
            # Если файл не в base_input_folder, просто меняем расширение
            output_path = pdf_path.with_suffix('.txt')
    elif output_path is None:
        output_path = pdf_path.with_suffix('.txt')
    else:
        output_path = Path(output_path)

    # Создаём родительские папки
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Конвертация: {pdf_path.name} -> {output_path.name}")
    print(f"Очистка текста: {'Включена' if clean else 'Выключена'}")

    text = extract_text_from_pdf(pdf_path, clean=clean)

    if text:
        if clean:
            text = remove_noise_lines(text)

        if save_text_to_file(text, output_path):
            stats = get_text_statistics(text)
            print(f"✓ Успешно сохранён в UTF-8")
            print(f"  Символов: {stats['chars']:,} | Слов: {stats['words']:,}")
            return True
        else:
            print(f"✗ Ошибка при сохранении")
            return False
    else:
        print(f"✗ Не удалось извлечь текст")
        return False


# Альтернативная версия с использованием pdfplumber (лучше извлекает таблицы)
def extract_text_with_pdfplumber(pdf_path, clean=True):
    """Альтернативный метод извлечения текста с помощью pdfplumber."""
    try:
        import pdfplumber

        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    if clean:
                        page_text = clean_text_for_rag(page_text)
                    text += page_text + "\n"
                else:
                    # Пробуем извлечь таблицы, если нет обычного текста
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            for row in table:
                                row_text = " | ".join(str(cell) if cell else "" for cell in row)
                                if clean:
                                    row_text = clean_text_for_rag(row_text)
                                text += row_text + "\n"

        if text.strip():
            if clean:
                text = clean_text_for_rag(text)
                text = remove_noise_lines(text)
            return text
        return None

    except ImportError:
        print("  pdfplumber не установлен. Используйте: pip install pdfplumber")
        return None
    except Exception as e:
        print(f"  Ошибка при использовании pdfplumber: {str(e)}")
        return None


def convert_pdfs_advanced(input_folder="downloaded_documents", output_folder="txt_documents", use_pdfplumber=False,
                          clean=True):
    """
    Расширенная версия конвертации с выбором библиотеки и сохранением структуры.
    """
    input_path = Path(input_folder)
    output_path = Path(output_folder)

    if not input_path.exists():
        print(f"❌ Папка '{input_folder}' не найдена!")
        return

    # Находим все подпапки
    categories = [d for d in input_path.iterdir() if d.is_dir()]

    if not categories:
        print(f"❌ В папке '{input_folder}' нет вложенных папок с категориями!")
        return

    print(f"📁 Найдено категорий: {len(categories)}")
    print(f"📂 Входная папка: {input_folder}")
    print(f"📂 Выходная папка: {output_folder}")
    print(f"🔧 Используемая библиотека: {'pdfplumber' if use_pdfplumber else 'PyPDF2'}")
    print(f"🧹 Очистка текста: {'Включена' if clean else 'Выключена'}")
    print("=" * 60)

    successful = 0
    failed = 0
    total_pdfs = 0
    total_chars = 0

    for category_path in categories:
        category_name = category_path.name
        print(f"\n📂 Категория: {category_name}")

        pdf_files = list(category_path.glob("*.pdf"))

        if not pdf_files:
            print(f"   ⚠ Нет PDF файлов")
            continue

        print(f"   📄 Найдено PDF: {len(pdf_files)}")

        category_output_path = output_path / category_name
        category_output_path.mkdir(parents=True, exist_ok=True)

        for pdf_path in pdf_files:
            total_pdfs += 1
            print(f"\n   [{total_pdfs}] Обработка: {pdf_path.name}")

            # Выбираем метод извлечения
            if use_pdfplumber:
                text = extract_text_with_pdfplumber(pdf_path, clean=clean)
            else:
                text = extract_text_from_pdf(pdf_path, clean=clean)

            if text:
                output_filename = pdf_path.stem + ".txt"
                output_filepath = category_output_path / output_filename

                if save_text_to_file(text, output_filepath):
                    file_size = output_filepath.stat().st_size
                    stats = get_text_statistics(text)
                    total_chars += stats['chars']
                    print(f"       ✓ Сохранён: {output_filename} ({file_size:,} байт)")
                    print(f"         Символов: {stats['chars']:,} | Слов: {stats['words']:,}")
                    successful += 1
                else:
                    print(f"       ✗ Ошибка при сохранении")
                    failed += 1
            else:
                print(f"       ✗ Не удалось извлечь текст")
                failed += 1

    print("\n" + "=" * 60)
    print(f"📊 ИТОГИ КОНВЕРТАЦИИ:")
    print(f"   ✅ Успешно: {successful}")
    print(f"   ❌ Ошибок: {failed}")
    print(f"   📁 Всего PDF: {total_pdfs}")
    print(f"   📝 Всего символов: {total_chars:,}")
    print(f"\n📂 TXT файлы сохранены в папке: {output_folder}")
    print(f"   Структура папок сохранена!")


def batch_process_for_rag(input_folder="downloaded_documents", output_folder="txt_documents"):
    """
    Специализированная функция для подготовки текстов к RAG.
    Сохраняет структуру вложенных папок.
    """
    print("\n" + "=" * 60)
    print("🔄 ПОДГОТОВКА ТЕКСТОВ ДЛЯ RAG СИСТЕМЫ")
    print("=" * 60)
    print(f"📂 Входная папка: {input_folder}")
    print(f"📂 Выходная папка: {output_folder}")
    print("📁 Структура папок будет сохранена!")
    print("=" * 60)

    convert_pdfs_to_txt(
        input_folder=input_folder,
        output_folder=output_folder,
        clean=True,
        min_line_length=8
    )

    # Создаём дополнительный файл с объединённым текстом по категориям
    output_path = Path(output_folder)
    categories = [d for d in output_path.iterdir() if d.is_dir()]

    if categories:
        # Создаём общий объединённый файл
        combined_path = output_path / "_all_texts_combined.txt"
        with open(combined_path, 'w', encoding='utf-8') as outfile:
            outfile.write("=" * 70 + "\n")
            outfile.write("ОБЪЕДИНЁННЫЙ ТЕКСТ ВСЕХ PDF ДЛЯ RAG\n")
            outfile.write("=" * 70 + "\n\n")

            for category_path in sorted(categories):
                category_name = category_path.name
                txt_files = list(category_path.glob("*.txt"))
                txt_files = [f for f in txt_files if not f.name.startswith("_")]

                if txt_files:
                    outfile.write(f"\n{'=' * 70}\n")
                    outfile.write(f"КАТЕГОРИЯ: {category_name}\n")
                    outfile.write(f"{'=' * 70}\n\n")

                    for txt_file in sorted(txt_files):
                        outfile.write(f"\n{'-' * 50}\n")
                        outfile.write(f"ФАЙЛ: {txt_file.name}\n")
                        outfile.write(f"{'-' * 50}\n\n")

                        with open(txt_file, 'r', encoding='utf-8') as infile:
                            outfile.write(infile.read())
                        outfile.write("\n\n")

        print(f"\n✓ Объединённый файл создан: {combined_path}")

        # Создаём отдельные объединённые файлы для каждой категории
        for category_path in categories:
            category_name = category_path.name
            txt_files = list(category_path.glob("*.txt"))
            txt_files = [f for f in txt_files if not f.name.startswith("_")]

            if txt_files:
                category_combined = category_path / f"_{category_name}_combined.txt"
                with open(category_combined, 'w', encoding='utf-8') as outfile:
                    outfile.write(f"ОБЪЕДИНЁННЫЙ ТЕКСТ ПО КАТЕГОРИИ: {category_name}\n")
                    outfile.write("=" * 70 + "\n\n")

                    for txt_file in sorted(txt_files):
                        outfile.write(f"\n{'-' * 50}\n")
                        outfile.write(f"ФАЙЛ: {txt_file.name}\n")
                        outfile.write(f"{'-' * 50}\n\n")

                        with open(txt_file, 'r', encoding='utf-8') as infile:
                            outfile.write(infile.read())
                        outfile.write("\n\n")

                print(f"✓ Объединённый файл для категории '{category_name}': {category_combined}")


if __name__ == "__main__":
    # Основной режим: подготовка текстов для RAG с сохранением структуры
    # Ожидается папка "downloaded_documents" с вложенными категориями и PDF-файлами
    batch_process_for_rag(input_folder="downloaded_documents", output_folder="txt_documents")

    # Альтернативные варианты использования:

    # 1. Конвертация всех PDF из "downloaded_documents" в "txt_documents" с сохранением структуры
    # convert_pdfs_to_txt(input_folder="downloaded_documents", output_folder="txt_documents", clean=True)

    # 2. Конвертация одного конкретного файла с сохранением структуры
    # convert_single_pdf("downloaded_documents/Устав образовательной организации/Устав.pdf", clean=True)

    # 3. Использование pdfplumber (лучше для таблиц) с сохранением структуры
    # pip install pdfplumber
    # convert_pdfs_advanced(input_folder="downloaded_documents", output_folder="txt_documents", use_pdfplumber=True, clean=True)