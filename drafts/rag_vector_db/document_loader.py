"""
Загрузка документов разных форматов.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class DocumentLoader:
    """Класс для загрузки документов"""

    def load_all_documents(self, folder_path: str) -> List[Dict[str, Any]]:
        """Загрузка всех документов из папки"""
        folder = Path(folder_path)
        documents = []

        if not folder.exists():
            logger.warning(f"Директория не существует: {folder}")
            return documents

        # Поддерживаемые форматы
        supported_extensions = {'.txt', '.pdf', '.docx'}

        for filepath in folder.glob("*"):
            if filepath.suffix.lower() in supported_extensions:
                try:
                    text = self._load_file(filepath)
                    if text.strip():
                        documents.append({
                            'text': text,
                            'source': filepath.name,
                            'path': str(filepath)
                        })
                        logger.debug(f"Загружен файл: {filepath.name}")
                except Exception as e:
                    logger.error(f"Ошибка загрузки {filepath}: {e}")

        logger.info(f"Загружено {len(documents)} документов из {folder}")
        return documents

    def _load_file(self, filepath: Path) -> str:
        """Загрузка конкретного файла"""
        if filepath.suffix.lower() == '.txt':
            return self._load_txt(filepath)
        elif filepath.suffix.lower() == '.pdf':
            return self._load_pdf(filepath)
        elif filepath.suffix.lower() == '.docx':
            return self._load_docx(filepath)
        else:
            return ""

    def _load_txt(self, filepath: Path) -> str:
        """Загрузка текстового файла"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Ошибка чтения TXT {filepath}: {e}")
            return ""

    def _load_pdf(self, filepath: Path) -> str:
        """Загрузка PDF файла"""
        try:
            import PyPDF2
            text = ""
            with open(filepath, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except ImportError:
            logger.error("PyPDF2 не установлен. Установите: pip install PyPDF2")
            return ""
        except Exception as e:
            logger.error(f"Ошибка чтения PDF {filepath}: {e}")
            return ""

    def _load_docx(self, filepath: Path) -> str:
        """Загрузка DOCX файла"""
        try:
            from docx import Document
            doc = Document(filepath)
            return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except ImportError:
            logger.error("python-docx не установлен. Установите: pip install python-docx")
            return ""
        except Exception as e:
            logger.error(f"Ошибка чтения DOCX {filepath}: {e}")
            return ""


# Создаем глобальный экземпляр для удобства
loader = DocumentLoader()