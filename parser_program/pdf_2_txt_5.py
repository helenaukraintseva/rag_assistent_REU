import os
import pdfplumber
from pathlib import Path


def extract_text_from_pdf(pdf_path):
    """Извлекает текст из PDF-файла используя pdfplumber"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        print(f"Ошибка при чтении {pdf_path}: {e}")
        return None


def process_pdfs_in_folder(root_folder):
    """Обходит все подпапки и обрабатывает PDF файлы"""
    root_path = Path(root_folder)

    if not root_path.exists():
        print(f"Папка {root_folder} не существует!")
        return

    total_pdfs = 0
    successful = 0
    failed = 0

    for current_folder in root_path.rglob('*'):
        if current_folder.is_dir():
            pdf_files = list(current_folder.glob('*.pdf')) + list(current_folder.glob('*.PDF'))

            for pdf_file in pdf_files:
                total_pdfs += 1
                print(f"Обработка: {pdf_file}")

                text = extract_text_from_pdf(pdf_file)

                if text and text.strip():
                    txt_file = pdf_file.with_suffix('.txt')
                    try:
                        with open(txt_file, 'w', encoding='utf-8') as f:
                            f.write(text)
                        print(f"  ✓ Сохранен: {txt_file}")
                        successful += 1
                    except Exception as e:
                        print(f"  ✗ Ошибка сохранения: {e}")
                        failed += 1
                else:
                    print(f"  ✗ Не удалось извлечь текст")
                    failed += 1

    print(f"\n{'=' * 50}")
    print(f"Готово! Обработано {successful} из {total_pdfs} PDF файлов")
    print(f"{'=' * 50}")


def main():
    folder_name = "downloaded_documents"
    process_pdfs_in_folder(folder_name)


if __name__ == "__main__":
    main()