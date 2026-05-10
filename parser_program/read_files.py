import os
import PyPDF2
from pathlib import Path
import sys


def extract_text_from_pdf(pdf_path):
    """
    Извлекает текст из PDF-файла.

    Args:
        pdf_path (str): Путь к PDF-файлу

    Returns:
        str: Извлеченный текст или None в случае ошибки
    """
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            # Создаем объект для чтения PDF
            pdf_reader = PyPDF2.PdfReader(file)

            # Получаем количество страниц
            num_pages = len(pdf_reader.pages)

            # Извлекаем текст с каждой страницы
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Страница {page_num + 1} ---\n"
                    text += page_text
                else:
                    text += f"\n--- Страница {page_num + 1} (текст не извлечен) ---\n"

            return text if text.strip() else None

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


def convert_pdfs_to_txt(input_folder="downloads", output_folder="txt_output"):
    """
    Конвертирует все PDF-файлы из папки в текстовые файлы.

    Args:
        input_folder (str): Папка с PDF-файлами
        output_folder (str): Папка для сохранения TXT-файлов
    """
    # Создаем папку для выходных файлов, если её нет
    Path(output_folder).mkdir(parents=True, exist_ok=True)

    # Получаем список всех PDF-файлов
    pdf_files = list(Path(input_folder).glob("*.pdf"))

    if not pdf_files:
        print(f"PDF-файлы не найдены в папке '{input_folder}'")
        return

    print(f"Найдено PDF-файлов: {len(pdf_files)}")
    print("=" * 60)

    successful = 0
    failed = 0

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Обработка: {pdf_path.name}")

        # Извлекаем текст из PDF
        text = extract_text_from_pdf(pdf_path)

        if text:
            # Создаем имя для выходного файла
            output_filename = pdf_path.stem + ".txt"
            output_path = Path(output_folder) / output_filename

            # Сохраняем текст в UTF-8
            if save_text_to_file(text, output_path):
                print(f"  ✓ Сохранён: {output_path}")
                successful += 1
            else:
                failed += 1
        else:
            print(f"  ✗ Не удалось извлечь текст")
            failed += 1

        print()

    print("=" * 60)
    print(f"Готово! Успешно: {successful}, Ошибок: {failed}")
    print(f"Текстовые файлы сохранены в папке: {output_folder}")


def convert_single_pdf(pdf_path, output_path=None):
    """
    Конвертирует один PDF-файл в текстовый.

    Args:
        pdf_path (str): Путь к PDF-файлу
        output_path (str, optional): Путь для сохранения TXT-файла
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

    text = extract_text_from_pdf(pdf_path)

    if text:
        if save_text_to_file(text, output_path):
            print(f"✓ Успешно сохранён в UTF-8")
            return True
        else:
            print(f"✗ Ошибка при сохранении")
            return False
    else:
        print(f"✗ Не удалось извлечь текст")
        return False


# Альтернативная версия с использованием pdfplumber (лучше извлекает таблицы)
def extract_text_with_pdfplumber(pdf_path):
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
                    text += f"\n--- Страница {page_num} ---\n"
                    text += page_text
                else:
                    # Пробуем извлечь таблицы, если нет обычного текста
                    tables = page.extract_tables()
                    if tables:
                        text += f"\n--- Страница {page_num} (таблицы) ---\n"
                        for table in tables:
                            for row in table:
                                text += " | ".join(str(cell) if cell else "" for cell in row) + "\n"
                    else:
                        text += f"\n--- Страница {page_num} (текст не извлечен) ---\n"

        return text if text.strip() else None

    except ImportError:
        print("  pdfplumber не установлен. Используйте: pip install pdfplumber")
        return None
    except Exception as e:
        print(f"  Ошибка при использовании pdfplumber: {str(e)}")
        return None


def convert_pdfs_advanced(input_folder="downloads", output_folder="txt_output", use_pdfplumber=False):
    """
    Расширенная версия конвертации с выбором библиотеки.

    Args:
        input_folder (str): Папка с PDF-файлами
        output_folder (str): Папка для сохранения TXT-файлов
        use_pdfplumber (bool): Использовать pdfplumber вместо PyPDF2
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
    print("=" * 60)

    successful = 0
    failed = 0

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Обработка: {pdf_path.name}")

        # Выбираем метод извлечения
        if use_pdfplumber:
            text = extract_text_with_pdfplumber(pdf_path)
        else:
            text = extract_text_from_pdf(pdf_path)

        if text:
            output_filename = pdf_path.stem + ".txt"
            output_path = Path(output_folder) / output_filename

            if save_text_to_file(text, output_path):
                file_size = output_path.stat().st_size
                print(f"  ✓ Сохранён: {output_filename} ({file_size:,} байт)")
                successful += 1
            else:
                failed += 1
        else:
            print(f"  ✗ Не удалось извлечь текст")
            failed += 1

        print()

    print("=" * 60)
    print(f"Готово! Успешно: {successful}, Ошибок: {failed}")
    print(f"Текстовые файлы сохранены в папке: {output_folder}")


if __name__ == "__main__":
    # Пример 1: Конвертация всех PDF из папки "downloads" в "txt_output"
    convert_pdfs_to_txt(input_folder="downloaded", output_folder="txt_output")

    # Пример 2: Конвертация одного конкретного файла
    # convert_single_pdf("downloads/02_spo_plan_Bryansk.pdf")

    # Пример 3: Использование pdfplumber (лучше для таблиц)
    # Для использования сначала установите: pip install pdfplumber
    # convert_pdfs_advanced(input_folder="downloads", output_folder="txt_output_advanced", use_pdfplumber=True)