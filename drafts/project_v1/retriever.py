"""
Модуль для поиска релевантных ключей в базе знаний.
Теперь работает только с ключами, а не с содержимым.
"""

from typing import List, Dict, Any, Optional
import logging
from knowledge_base import kb

logger = logging.getLogger(__name__)


class SearchResult:
    """Результат поиска - содержит только ключ и метаданные"""

    def __init__(self, key: str, title: str, category: str, score: float, keywords: List[str], last_updated: str):
        self.key = key
        self.title = title
        self.category = category
        self.score = score
        self.keywords = keywords
        self.last_updated = last_updated

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "category": self.category,
            "score": self.score,
            "keywords": self.keywords,
            "last_updated": self.last_updated
        }


class KeyRetriever:
    """
    Класс для поиска релевантных ключей в базе знаний.
    Не возвращает содержимое документов!
    """

    def __init__(self):
        self.kb = kb

    def search(self, query: str, top_k: int = 5, threshold: float = 0.1) -> List[SearchResult]:
        """
        Поиск релевантных ключей по запросу.
        Возвращает объекты SearchResult (без содержимого).
        """
        if not query or not self.kb.health_check()['loaded']:
            return []

        # Получаем релевантные ключи из базы знаний
        key_results = self.kb.search_keys(query, top_k=top_k)

        # Преобразуем в SearchResult
        results = []
        for key_data in key_results:
            if key_data['score'] >= threshold:
                results.append(SearchResult(
                    key=key_data['key'],
                    title=key_data['title'],
                    category=key_data['category'],
                    score=key_data['score'],
                    keywords=key_data['keywords'],
                    last_updated=key_data['last_updated']
                ))

        return results

    def get_key_info(self, key: str) -> Optional[Dict[str, Any]]:
        """Получение информации о конкретном ключе (без содержимого)"""
        if key in self.kb.knowledge_base:
            data = self.kb.knowledge_base[key]
            return {
                "key": key,
                "title": data.get('title', key),
                "category": data.get('category', 'general'),
                "keywords": data.get('keywords', []),
                "last_updated": data.get('last_updated', 'unknown')
            }
        return None

    def health_check(self) -> Dict[str, Any]:
        """Проверка состояния ретривера"""
        return self.kb.health_check()

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        return {
            "total_keys": len(self.kb.get_all_keys()),
            "index_size": len(self.kb.key_index),
            "sample_keys": self.kb.get_all_keys()[:5]
        }


def get_retriever() -> KeyRetriever:
    """Фабрика для создания ретривера"""
    return KeyRetriever()