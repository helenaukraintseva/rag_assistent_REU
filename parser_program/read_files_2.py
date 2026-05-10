import os
import re
import PyPDF2
from pathlib import Path
import sys


def clean_text_for_rag(text):
    """
    Очищает текст от лишних символов и нормализует пробелы для использования в RAG.

    Args:
        text (str): Исходный текст

    Returns:
        str: Очищенный текст
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

    Args:
        text (str): Исходный текст
        min_line_length (int): Минимальная длина строки для сохранения

    Returns:
        str: Очищенный текст
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

    Args:
        pdf_path (str): Путь к PDF-файлу
        clean (bool): Очищать ли текст от лишних символов

    Returns:
        str: Извлеченный и очищенный текст или None в случае ошибки
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
    """
    Сохраняет текст в UTF-8 формате.

    Args:
        text (str): Текст для сохранения
        output_path (str): Путь к выходному файлу
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        return True
    except Exception as e:
        print(f"  Ошибка при сохранении {output_path}: {str(e)}")
        return False


def get_text_statistics(text):
    """
    Возвращает статистику по тексту.

    Args:
        text (str): Текст для анализа

    Returns:
        dict: Словарь со статистикой
    """
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
        "pages_approx": max(1, len(non_empty_lines) // 40)  # примерно 40 строк на страницу
    }


def convert_pdfs_to_txt(input_folder="downloads", output_folder="txt_output", clean=True, min_line_length=10):
    """
    Конвертирует все PDF-файлы из папки в текстовые файлы с очисткой.

    Args:
        input_folder (str): Папка с PDF-файлами
        output_folder (str): Папка для сохранения TXT-файлов
        clean (bool): Очищать ли текст от лишних символов
        min_line_length (int): Минимальная длина строки для очистки
    """
    # Создаем папку для выходных файлов, если её нет
    Path(output_folder).mkdir(parents=True, exist_ok=True)

    # Получаем список всех PDF-файлов
    pdf_files = list(Path(input_folder).glob("*.pdf"))

    if not pdf_files:
        print(f"PDF-файлы не найдены в папке '{input_folder}'")
        return

    print(f"Найдено PDF-файлов: {len(pdf_files)}")
    print(f"Очистка текста: {'Включена' if clean else 'Выключена'}")
    print("=" * 60)

    # Лог для статистики
    statistics_log = []
    successful = 0
    failed = 0

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Обработка: {pdf_path.name}")

        # Извлекаем текст из PDF
        text = extract_text_from_pdf(pdf_path, clean=clean)

        if text:
            # Применяем дополнительную очистку строк
            if clean:
                text = remove_noise_lines(text, min_line_length=min_line_length)

            # Создаем имя для выходного файла
            output_filename = pdf_path.stem + ".txt"
            output_path = Path(output_folder) / output_filename

            # Сохраняем текст
            if save_text_to_file(text, output_path):
                stats = get_text_statistics(text)
                statistics_log.append({
                    "file": pdf_path.name,
                    "output": output_filename,
                    "stats": stats
                })

                print(f"  ✓ Сохранён: {output_path}")
                print(
                    f"    Символов: {stats['chars']:,} | Слов: {stats['words']:,} | Строк: {stats['non_empty_lines']}")
                successful += 1
            else:
                failed += 1
        else:
            print(f"  ✗ Не удалось извлечь текст")
            failed += 1

        print()

    # Сохраняем статистику
    if statistics_log and clean:
        stats_path = Path(output_folder) / "_conversion_stats.txt"
        with open(stats_path, 'w', encoding='utf-8') as f:
            f.write("СТАТИСТИКА КОНВЕРТАЦИИ PDF -> TXT\n")
            f.write("=" * 50 + "\n\n")
            total_chars = 0
            total_words = 0
            for log in statistics_log:
                f.write(f"Файл: {log['file']}\n")
                f.write(f"  -> {log['output']}\n")
                f.write(f"  Символов: {log['stats']['chars']:,}\n")
                f.write(f"  Слов: {log['stats']['words']:,}\n")
                f.write(f"  Строк: {log['stats']['non_empty_lines']}\n")
                f.write(f"  Примерно страниц: {log['stats']['pages_approx']}\n\n")
                total_chars += log['stats']['chars']
                total_words += log['stats']['words']

            f.write("=" * 50 + "\n")
            f.write(f"ВСЕГО:\n")
            f.write(f"  Файлов: {successful}\n")
            f.write(f"  Символов: {total_chars:,}\n")
            f.write(f"  Слов: {total_words:,}\n")

    print("=" * 60)
    print(f"Готово! Успешно: {successful}, Ошибок: {failed}")
    print(f"Текстовые файлы сохранены в папке: {output_folder}")
    if clean:
        print(f"Статистика сохранена в: {output_folder}/_conversion_stats.txt")


def convert_single_pdf(pdf_path, output_path=None, clean=True):
    """
    Конвертирует один PDF-файл в текстовый с очисткой.

    Args:
        pdf_path (str): Путь к PDF-файлу
        output_path (str, optional): Путь для сохранения TXT-файла
        clean (bool): Очищать ли текст от лишних символов
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        print(f"Файл не найден: {pdf_path}")
        return False

    if output_path is None:
        output_path = pdf_path.with_suffix('.txt')
    else:
        output_path = Path(output_path)

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
    """
    Альтернативный метод извлечения текста с помощью pdfplumber.
    Требует установки: pip install pdfplumber
    """
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


def convert_pdfs_advanced(input_folder="downloads", output_folder="txt_output", use_pdfplumber=False, clean=True):
    """
    Расширенная версия конвертации с выбором библиотеки.

    Args:
        input_folder (str): Папка с PDF-файлами
        output_folder (str): Папка для сохранения TXT-файлов
        use_pdfplumber (bool): Использовать pdfplumber вместо PyPDF2
        clean (bool): Очищать ли текст от лишних символов
    """
    # Создаем папку для выходных файлов
    Path(output_folder).mkdir(parents=True, exist_ok=True)

    # Получаем список всех PDF-файлов
    pdf_files = list(Path(input_folder).glob("*.pdf"))

    if not pdf_files:
        print(f"PDF-файлы не найдены в папке '{input_folder}'")
        return

    print(f"Найдено PDF-файлов: {len(pdf_files)}")
    print(f"Используемая библиотека: {'pdfplumber' if use_pdfplumber else 'PyPDF2'}")
    print(f"Очистка текста: {'Включена' if clean else 'Выключена'}")
    print("=" * 60)

    successful = 0
    failed = 0
    total_chars = 0

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Обработка: {pdf_path.name}")

        # Выбираем метод извлечения
        if use_pdfplumber:
            text = extract_text_with_pdfplumber(pdf_path, clean=clean)
        else:
            text = extract_text_from_pdf(pdf_path, clean=clean)

        if text:
            output_filename = pdf_path.stem + ".txt"
            output_path = Path(output_folder) / output_filename

            if save_text_to_file(text, output_path):
                file_size = output_path.stat().st_size
                stats = get_text_statistics(text)
                total_chars += stats['chars']
                print(f"  ✓ Сохранён: {output_filename} ({file_size:,} байт)")
                print(f"    Символов: {stats['chars']:,} | Слов: {stats['words']:,}")
                successful += 1
            else:
                failed += 1
        else:
            print(f"  ✗ Не удалось извлечь текст")
            failed += 1

        print()

    print("=" * 60)
    print(f"Готово! Успешно: {successful}, Ошибок: {failed}")
    print(f"Всего символов в извлечённых текстах: {total_chars:,}")
    print(f"Текстовые файлы сохранены в папке: {output_folder}")


def batch_process_for_rag(input_folder="downloaded", output_folder="rag_ready_texts"):
    """
    Специализированная функция для подготовки текстов к RAG.
    Максимальная очистка и нормализация.

    Args:
        input_folder (str): Папка с PDF-файлами
        output_folder (str): Папка для сохранения очищенных TXT-файлов
    """
    print("\n" + "=" * 60)
    print("ПОДГОТОВКА ТЕКСТОВ ДЛЯ RAG СИСТЕМЫ")
    print("=" * 60)

    convert_pdfs_to_txt(
        input_folder=input_folder,
        output_folder=output_folder,
        clean=True,
        min_line_length=8
    )

    # Создаём дополнительный файл с объединённым текстом для удобного просмотра
    output_path = Path(output_folder)
    txt_files = list(output_path.glob("*.txt"))
    txt_files = [f for f in txt_files if not f.name.startswith("_")]

    if txt_files:
        combined_path = output_path / "_all_texts_combined.txt"
        with open(combined_path, 'w', encoding='utf-8') as outfile:
            outfile.write("=" * 70 + "\n")
            outfile.write("ОБЪЕДИНЁННЫЙ ТЕКСТ ВСЕХ PDF ДЛЯ RAG\n")
            outfile.write("=" * 70 + "\n\n")

            for txt_file in sorted(txt_files):
                outfile.write(f"\n{'=' * 70}\n")
                outfile.write(f"ФАЙЛ: {txt_file.name}\n")
                outfile.write(f"{'=' * 70}\n\n")

                with open(txt_file, 'r', encoding='utf-8') as infile:
                    outfile.write(infile.read())
                outfile.write("\n\n")

        print(f"\n✓ Объединённый файл создан: {combined_path}")


if __name__ == "__main__":
    # Основной режим: подготовка текстов для RAG
    # Ожидается папка "downloaded" с PDF-файлами
    batch_process_for_rag(input_folder="downloaded", output_folder="rag_ready_texts")

    # Альтернативные варианты использования:

    # 1. Конвертация всех PDF из папки "downloads" в "txt_output" с очисткой
    # convert_pdfs_to_txt(input_folder="downloads", output_folder="txt_output", clean=True)

    # 2. Конвертация одного конкретного файла
    # convert_single_pdf("downloaded/02_spo_plan_Bryansk.pdf", clean=True)

    # 3. Использование pdfplumber (лучше для таблиц)
    # pip install pdfplumber
    # convert_pdfs_advanced(input_folder="downloaded", output_folder="txt_output_advanced", use_pdfplumber=True, clean=True)