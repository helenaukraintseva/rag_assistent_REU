"""
Разбиение текста на фрагменты для обработки.
"""

import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class TextSplitter:
    """Класс для разбиения текста на фрагменты"""

    def split_documents(self,
                        documents: List[Dict[str, Any]],
                        chunk_size: int = 1000,
                        overlap: int = 200) -> List[Dict[str, Any]]:
        """Разбиение документов на фрагменты"""
        all_chunks = []

        for doc_idx, doc in enumerate(documents):
            text = doc.get('text', '')
            if not text.strip():
                continue

            # Разбиваем текст на фрагменты
            text_chunks = self._split_text(text, chunk_size, overlap)

            # Создаем структурированные фрагменты
            for chunk_idx, chunk_text in enumerate(text_chunks):
                chunk_data = {
                    'text': chunk_text,
                    'metadata': {
                        'source': doc.get('source', f'document_{doc_idx}'),
                        'path': doc.get('path', ''),
                        'chunk_id': chunk_idx,
                        'total_chunks': len(text_chunks),
                        'document_index': doc_idx,
                        'timestamp': '2024-01-01'  # Можно добавить реальное время
                    }
                }
                all_chunks.append(chunk_data)

        logger.info(f"Создано {len(all_chunks)} фрагментов из {len(documents)} документов")
        return all_chunks

    def _split_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Разбивает текст на фрагменты заданного размера с перекрытием"""
        if not text:
            return []

        # Очистка текста
        text = re.sub(r'\s+', ' ', text).strip()

        # Если текст меньше размера чанка, возвращаем как есть
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            # Определяем конец фрагмента
            end = start + chunk_size

            # Если это не первый фрагмент, добавляем перекрытие
            if start > 0 and overlap > 0:
                # Ищем границу предложения для лучшего разделения
                overlap_start = max(start - overlap, 0)
                # Пытаемся найти границу предложения в области перекрытия
                sentence_boundary = self._find_sentence_boundary(text, overlap_start, start)
                if sentence_boundary > overlap_start:
                    start = sentence_boundary

            # Если это последний фрагмент
            if end >= len(text):
                chunks.append(text[start:].strip())
                break

            # Ищем границу предложения для разрыва
            boundary = self._find_sentence_boundary(text, start, end)
            if boundary > start:
                end = boundary

            chunks.append(text[start:end].strip())
            start = end

        # Удаляем пустые фрагменты
        return [chunk for chunk in chunks if chunk.strip()]

    def _find_sentence_boundary(self, text: str, start: int, end: int) -> int:
        """Находит границу предложения в заданном диапазоне"""
        # Ищем точки, восклицательные и вопросительные знаки
        boundary_chars = {'.', '!', '?', ';', '\n'}

        # Ищем с конца диапазона
        for i in range(min(end, len(text)) - 1, start, -1):
            if text[i] in boundary_chars:
                # Проверяем, что это не аббревиатура (например, "т.д.")
                if i > 0 and text[i - 1].isalpha() and text[i] == '.':
                    continue
                return i + 1  # +1 чтобы включить знак пунктуации

        # Если не нашли границу предложения, ищем пробел
        for i in range(min(end, len(text)) - 1, start, -1):
            if text[i] == ' ':
                return i + 1

        # Если ничего не нашли, возвращаем конец диапазона
        return end


# Создаем глобальный экземпляр
splitter = TextSplitter()