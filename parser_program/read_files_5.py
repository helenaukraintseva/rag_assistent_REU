import os
import re
import PyPDF2
from pathlib import Path
import sys
import subprocess


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


def extract_text_with_pypdf2(pdf_path, clean=True):
    """Извлечение текста с помощью PyPDF2 (базовый метод)."""
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)

            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                else:
                    # Пробуем альтернативный метод извлечения
                    try:
                        page_text = page.extract_text(extraction_mode="layout")
                        if page_text:
                            text += page_text + "\n"
                    except:
                        pass

        if text.strip():
            if clean:
                text = clean_text_for_rag(text)
            return text
        return None
    except Exception as e:
        print(f"    PyPDF2 ошибка: {str(e)[:100]}")
        return None


def extract_text_with_pdfplumber(pdf_path, clean=True):
    """Извлечение текста с помощью pdfplumber (лучше для таблиц и сложных макетов)."""
    try:
        import pdfplumber

        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                else:
                    # Пробуем извлечь таблицы
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            for row in table:
                                row_text = " | ".join(str(cell) if cell else "" for cell in row)
                                if row_text.strip():
                                    text += row_text + "\n"
                    else:
                        # Пробуем extract_words для скан-копий
                        words = page.extract_words()
                        if words:
                            # Группируем слова по строкам
                            lines = {}
                            for word in words:
                                y = round(word['top'] / 10)  # Группируем по вертикали
                                if y not in lines:
                                    lines[y] = []
                                lines[y].append((word['x0'], word['text']))

                            for y in sorted(lines.keys()):
                                line = ' '.join([word[1] for word in sorted(lines[y], key=lambda x: x[0])])
                                if line.strip():
                                    text += line + "\n"

        if text.strip():
            if clean:
                text = clean_text_for_rag(text)
            return text
        return None
    except ImportError:
        print("    pdfplumber не установлен")
        return None
    except Exception as e:
        print(f"    pdfplumber ошибка: {str(e)[:100]}")
        return None


def extract_text_with_pdfminer(pdf_path, clean=True):
    """Извлечение текста с помощью pdfminer.six (хорошо для сложных PDF)."""
    try:
        from pdfminer.high_level import extract_text

        text = extract_text(pdf_path)

        if text and text.strip():
            if clean:
                text = clean_text_for_rag(text)
            return text
        return None
    except ImportError:
        print("    pdfminer.six не установлен. Установите: pip install pdfminer.six")
        return None
    except Exception as e:
        print(f"    pdfminer ошибка: {str(e)[:100]}")
        return None


def extract_text_with_poppler(pdf_path, clean=True):
    """Извлечение текста с помощью pdftotext (через poppler-utils)."""
    try:
        import pdftotext

        with open(pdf_path, 'rb') as file:
            pdf = pdftotext.PDF(file)
            text = "\n".join(pdf)

        if text and text.strip():
            if clean:
                text = clean_text_for_rag(text)
            return text
        return None
    except ImportError:
        print("    pdftotext не установлен. Установите: pip install pdftotext")
        return None
    except Exception as e:
        print(f"    pdftotext ошибка: {str(e)[:100]}")
        return None


def extract_text_ocr(pdf_path, clean=True):
    """Извлечение текста с помощью OCR (pytesseract) для сканированных PDF."""
    try:
        from pdf2image import convert_from_path
        import pytesseract

        # Конвертируем PDF в изображения
        images = convert_from_path(pdf_path, dpi=300)

        text = ""
        for i, image in enumerate(images):
            # Применяем OCR
            page_text = pytesseract.image_to_string(image, lang='rus+eng')
            text += page_text + "\n"

        if text.strip():
            if clean:
                text = clean_text_for_rag(text)
            return text
        return None
    except ImportError:
        print("    Требуются библиотеки: pip install pdf2image pytesseract")
        print("    Также нужен Tesseract OCR: https://github.com/tesseract-ocr/tesseract")
        return None
    except Exception as e:
        print(f"    OCR ошибка: {str(e)[:100]}")
        return None


def extract_text_from_pdf(pdf_path, clean=True, use_ocr_fallback=True):
    """
    Извлекает текст из PDF-файла, пробуя несколько методов.

    Методы в порядке приоритета:
    1. PyPDF2 (быстрый, базовый)
    2. pdfplumber (лучше для таблиц)
    3. pdfminer (для сложных PDF)
    4. pdftotext (альтернативный)
    5. OCR (для сканированных PDF)
    """
    methods = [
        ("PyPDF2", lambda: extract_text_with_pypdf2(pdf_path, clean)),
        ("pdfplumber", lambda: extract_text_with_pdfplumber(pdf_path, clean)),
        ("pdfminer", lambda: extract_text_with_pdfminer(pdf_path, clean)),
        ("pdftotext", lambda: extract_text_with_poppler(pdf_path, clean)),
    ]

    if use_ocr_fallback:
        methods.append(("OCR", lambda: extract_text_ocr(pdf_path, clean)))

    for method_name, method_func in methods:
        try:
            text = method_func()
            if text and len(text.strip()) > 100:  # Успешно, если есть хотя бы 100 символов
                print(f"    ✓ Успешно извлечено через {method_name} ({len(text):,} символов)")
                return text
            elif text and len(text.strip()) > 0:
                print(f"    ⚠ {method_name} извлёк мало текста ({len(text):,} символов)")
        except Exception as e:
            continue

    print(f"    ✗ Не удалось извлечь текст ни одним методом")
    return None


def save_text_to_file(text, output_path):
    """Сохраняет текст в UTF-8 формате."""
    try:
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


def convert_pdfs_to_txt(input_folder="downloaded_documents", output_folder="txt_documents",
                        clean=True, min_line_length=10, use_ocr_fallback=True):
    """
    Конвертирует все PDF-файлы из папки и её подпапок в текстовые файлы с сохранением структуры.
    Использует несколько методов извлечения текста.
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
    print(f"🔍 OCR для сканов: {'Включен' if use_ocr_fallback else 'Выключен'}")
    print("=" * 60)

    # Статистика
    statistics_log = []
    successful = 0
    failed = 0
    total_pdfs = 0
    method_stats = {"PyPDF2": 0, "pdfplumber": 0, "pdfminer": 0, "pdftotext": 0, "OCR": 0}

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

            # Пробуем извлечь текст разными методами
            text = extract_text_from_pdf(pdf_path, clean=clean, use_ocr_fallback=use_ocr_fallback)

            # Определяем, какой метод сработал (для статистики)
            if text:
                # Проверяем качество текста (не слишком ли мало символов)
                if len(text.strip()) < 50:
                    print(f"       ⚠ Текст очень короткий ({len(text):,} символов), возможно проблемы с распознаванием")

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

                    print(f"       ✓ Сохранён: {output_filepath.name}")
                    print(
                        f"         Символов: {stats['chars']:,} | Слов: {stats['words']:,} | Строк: {stats['non_empty_lines']}")
                    successful += 1
                else:
                    print(f"       ✗ Ошибка при сохранении")
                    failed += 1
            else:
                print(f"       ✗ Не удалось извлечь текст ни одним методом")
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
            f.write(f"Выходная папка: {output_folder}\n")
            f.write(f"OCR для сканов: {'Включен' if use_ocr_fallback else 'Выключен'}\n\n")

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
    print(f"   📈 Успешность: {successful / total_pdfs * 100:.1f}%" if total_pdfs > 0 else "")
    print(f"\n📂 TXT файлы сохранены в папке: {output_folder}")
    print(f"   Структура папок сохранена!")


def batch_process_for_rag(input_folder="downloaded_documents", output_folder="txt_documents", use_ocr_fallback=True):
    """
    Специализированная функция для подготовки текстов к RAG.
    Сохраняет структуру вложенных папок.

    Args:
        input_folder (str): Папка с PDF-файлами
        output_folder (str): Папка для сохранения TXT-файлов
        use_ocr_fallback (bool): Использовать ли OCR для сканированных PDF
    """
    print("\n" + "=" * 60)
    print("🔄 ПОДГОТОВКА ТЕКСТОВ ДЛЯ RAG СИСТЕМЫ")
    print("=" * 60)
    print(f"📂 Входная папка: {input_folder}")
    print(f"📂 Выходная папка: {output_folder}")
    print(f"🔍 OCR для сканов: {'Включен' if use_ocr_fallback else 'Выключен'}")
    print("📁 Структура папок будет сохранена!")
    print("=" * 60)
    print("\n💡 Для лучшего распознавания установите дополнительные библиотеки:")
    print("   pip install pdfplumber pdfminer.six pdf2image pytesseract")
    print("   А также Tesseract OCR: https://github.com/tesseract-ocr/tesseract")
    print("=" * 60)

    convert_pdfs_to_txt(
        input_folder=input_folder,
        output_folder=output_folder,
        clean=True,
        min_line_length=8,
        use_ocr_fallback=use_ocr_fallback
    )

    # Создаём дополнительный файл с объединённым текстом по категориям
    output_path = Path(output_folder)
    if output_path.exists():
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


def convert_problematic_pdf(pdf_path, output_path=None):
    """
    Специальная функция для конвертации "проблемных" PDF-файлов.
    Пробует все возможные методы и показывает детальную информацию.
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        print(f"❌ Файл не найден: {pdf_path}")
        return False

    print(f"\n🔍 Анализ проблемного PDF: {pdf_path.name}")
    print("=" * 50)

    # Пробуем все методы по очереди
    methods = [
        ("PyPDF2", lambda: extract_text_with_pypdf2(pdf_path, clean=False)),
        ("pdfplumber", lambda: extract_text_with_pdfplumber(pdf_path, clean=False)),
        ("pdfminer", lambda: extract_text_with_pdfminer(pdf_path, clean=False)),
        ("pdftotext", lambda: extract_text_with_poppler(pdf_path, clean=False)),
        ("OCR", lambda: extract_text_ocr(pdf_path, clean=False)),
    ]

    results = []
    for method_name, method_func in methods:
        try:
            text = method_func()
            if text:
                results.append((method_name, len(text.strip()), text[:200]))
                print(f"   ✓ {method_name}: {len(text):,} символов")
            else:
                print(f"   ✗ {method_name}: не удалось извлечь текст")
        except Exception as e:
            print(f"   ✗ {method_name}: ошибка - {str(e)[:50]}")
            results.append((method_name, 0, None))

    print("=" * 50)

    # Выбираем лучший результат
    best_method, best_length, best_text = max(results, key=lambda x: x[1])

    if best_length > 0:
        print(f"\n✅ Лучший результат: {best_method} ({best_length:,} символов)")

        if output_path is None:
            output_path = pdf_path.with_suffix('.txt')
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Очищаем текст
        cleaned_text = clean_text_for_rag(best_text)
        cleaned_text = remove_noise_lines(cleaned_text)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_text)

        print(f"✅ Текст сохранён в: {output_path}")
        return True
    else:
        print("\n❌ Не удалось извлечь текст ни одним методом")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Конвертация PDF в TXT с сохранением структуры')
    parser.add_argument('--input', type=str, default='downloaded_documents',
                        help='Входная папка с PDF (по умолчанию: downloaded_documents)')
    parser.add_argument('--output', type=str, default='txt_documents',
                        help='Выходная папка для TXT (по умолчанию: txt_documents)')
    parser.add_argument('--no-ocr', action='store_true',
                        help='Отключить OCR (для сканированных PDF)')
    parser.add_argument('--single', type=str, default=None,
                        help='Конвертировать один конкретный PDF файл')

    args = parser.parse_args()

    if args.single:
        # Конвертация одного проблемного файла
        convert_problematic_pdf(args.single)
    else:
        # Основной режим: пакетная конвертация
        batch_process_for_rag(
            input_folder=args.input,
            output_folder=args.output,
            use_ocr_fallback=not args.no_ocr
        )