"""
Модуль для работы с базой знаний в формате словаря.
Обеспечивает доступ к данным по ключам и поиск релевантных ключей.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """
    Класс для работы с базой знаний в формате словаря.
    Данные хранятся в формате: {ключ_документа: {текст, метаданные, ...}}
    """

    def __init__(self, kb_path: str = "data/knowledge_base.json"):
        self.kb_path = Path(kb_path)
        self.knowledge_base: Dict[str, Dict[str, Any]] = {}
        self.key_index: Dict[str, List[str]] = {}  # Индекс для поиска по ключевым словам
        self.load()

    def load(self) -> bool:
        """Загрузка базы знаний из JSON файла"""
        try:
            if not self.kb_path.exists():
                logger.warning(f"Файл базы знаний не найден: {self.kb_path}")
                self._create_sample_kb()
                return True

            with open(self.kb_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Проверяем формат данных
            if isinstance(data, dict):
                self.knowledge_base = data
            elif isinstance(data, list):
                # Конвертируем список в словарь с ключами из метаданных
                self.knowledge_base = {}
                for item in data:
                    key = item.get('key', item.get('id', item.get('title', str(len(self.knowledge_base)))))
                    self.knowledge_base[key] = item
            else:
                logger.error(f"Неверный формат базы знаний: {type(data)}")
                return False

            # Строим индекс для поиска
            self._build_index()
            logger.info(f"База знаний загружена: {len(self.knowledge_base)} записей")
            return True

        except Exception as e:
            logger.error(f"Ошибка загрузки базы знаний: {e}")
            return False

    def _create_sample_kb(self):
        """Создание примера базы знаний для тестирования"""
        self.knowledge_base = {
            "расписание_занятий_2_курс": {
                "title": "Расписание занятий для 2 курса",
                "category": "schedule",
                "content": """
                Расписание занятий для студентов 2 курса:
                Понедельник: 10:00-11:30 - Математический анализ (ауд. 301)
                            12:00-13:30 - Информатика (ауд. 405)
                Вторник:     10:00-11:30 - Физика (ауд. 215)
                Среда:       10:00-11:30 - Иностранный язык (ауд. 108)
                """,
                "keywords": ["расписание", "2 курс", "занятия", "пары"],
                "last_updated": "2026-02-20"
            },
            "правила_пересдачи_экзаменов": {
                "title": "Правила пересдачи экзаменов",
                "category": "academic",
                "content": """
                Правила пересдачи экзаменов:
                1. Первая пересдача проводится в течение 30 дней после сессии
                2. Вторая пересдача возможна через комиссию
                3. Для пересдачи необходимо подать заявление в учебный офис
                4. Стоимость пересдачи для платников: 2000 руб.
                """,
                "keywords": ["пересдача", "экзамен", "долги", "пересдать"],
                "last_updated": "2026-02-15"
            },
            "стипендия_социальная_документы": {
                "title": "Документы для оформления социальной стипендии",
                "category": "scholarship",
                "content": """
                Для оформления социальной стипендии необходимы:
                1. Заявление на имя ректора
                2. Справка из органов соцзащиты
                3. Копия паспорта
                4. Справка о доходах семьи (при необходимости)
                5. Документы, подтверждающие льготную категорию
                Срок подачи: до 10 числа каждого месяца
                """,
                "keywords": ["стипендия", "социальная", "документы", "оформление"],
                "last_updated": "2026-02-10"
            },
            "академический_отпуск_медицина": {
                "title": "Оформление академического отпуска по медицинским показаниям",
                "category": "administrative",
                "content": """
                Академический отпуск по медицинским показаниям:
                1. Медицинское заключение врачебной комиссии
                2. Заявление на имя ректора
                3. Академическая справка или справка об обучении
                4. Копия паспорта
                Срок рассмотрения: 10 рабочих дней
                """,
                "keywords": ["академический отпуск", "медицина", "болезнь", "отпуск"],
                "last_updated": "2026-02-18"
            }
        }
        self.save()
        self._build_index()
        logger.info("Создан пример базы знаний")

    def save(self):
        """Сохранение базы знаний в файл"""
        try:
            self.kb_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.kb_path, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_base, f, ensure_ascii=False, indent=2)
            logger.info(f"База знаний сохранена: {self.kb_path}")
        except Exception as e:
            logger.error(f"Ошибка сохранения базы знаний: {e}")

    def _build_index(self):
        """Построение поискового индекса по ключевым словам"""
        self.key_index = {}
        for key, data in self.knowledge_base.items():
            # Извлекаем ключевые слова из разных полей
            keywords = []

            # Из явного поля keywords
            if 'keywords' in data and isinstance(data['keywords'], list):
                keywords.extend([kw.lower() for kw in data['keywords']])

            # Из заголовка
            if 'title' in data:
                keywords.extend([word.lower() for word in data['title'].split()])

            # Из категории
            if 'category' in data:
                keywords.append(data['category'].lower())

            # Добавляем сам ключ как ключевое слово
            keywords.append(key.lower())

            # Убираем дубликаты
            keywords = list(set(keywords))

            # Индексируем каждое ключевое слово
            for kw in keywords:
                if kw not in self.key_index:
                    self.key_index[kw] = []
                if key not in self.key_index[kw]:
                    self.key_index[kw].append(key)

        logger.debug(f"Построен индекс: {len(self.key_index)} ключевых слов")

    def search_keys(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Поиск релевантных ключей по запросу.
        Возвращает только ключи и метаданные, без содержимого.
        """
        if not self.key_index:
            return []

        query_words = set(query.lower().split())
        key_scores = {}

        # Оцениваем релевантность каждого ключа
        for key in self.knowledge_base.keys():
            score = 0
            data = self.knowledge_base[key]

            # Проверяем совпадения с ключевыми словами
            keywords = []
            if 'keywords' in data:
                keywords.extend([kw.lower() for kw in data['keywords']])
            if 'category' in data:
                keywords.append(data['category'].lower())
            keywords.append(key.lower())

            # Считаем совпадения
            for kw in keywords:
                for q_word in query_words:
                    if q_word in kw or kw in q_word:
                        score += 1

            # Бонус за точное совпадение
            if any(q_word == key.lower() for q_word in query_words):
                score += 3

            if score > 0:
                key_scores[key] = score

        # Сортируем по релевантности
        sorted_keys = sorted(key_scores.items(), key=lambda x: x[1], reverse=True)

        # Возвращаем только ключи и метаданные (без content)
        results = []
        for key, score in sorted_keys[:top_k]:
            data = self.knowledge_base[key]
            results.append({
                "key": key,
                "title": data.get('title', key),
                "category": data.get('category', 'general'),
                "score": score / max(key_scores.values()) if key_scores else 0,
                "keywords": data.get('keywords', []),
                "last_updated": data.get('last_updated', 'unknown')
                # НЕТ ПОЛЯ content - ИИ получает только ключи
            })

        return results

    def get_content_by_key(self, key: str) -> Optional[str]:
        """Получение содержимого по ключу (для формирования ответа)"""
        if key in self.knowledge_base:
            return self.knowledge_base[key].get('content', '')
        return None

    def get_keys_info(self, keys: List[str]) -> Dict[str, Any]:
        """
        Получение информации о ключах (без содержимого) для отправки в ИИ.
        Это то, что получает языковая модель.
        """
        info = {}
        for key in keys:
            if key in self.knowledge_base:
                data = self.knowledge_base[key]
                info[key] = {
                    "title": data.get('title', key),
                    "category": data.get('category', 'general'),
                    "keywords": data.get('keywords', []),
                    "last_updated": data.get('last_updated', 'unknown')
                }
        return info

    def get_all_keys(self) -> List[str]:
        """Получение списка всех ключей"""
        return list(self.knowledge_base.keys())

    def add_entry(self, key: str, data: Dict[str, Any]):
        """Добавление новой записи в базу знаний"""
        self.knowledge_base[key] = data
        self._build_index()
        self.save()

    def health_check(self) -> Dict[str, Any]:
        """Проверка состояния базы знаний"""
        return {
            "loaded": len(self.knowledge_base) > 0,
            "total_entries": len(self.knowledge_base),
            "index_size": len(self.key_index),
            "keys": list(self.knowledge_base.keys())[:10]  # первые 10 ключей для информации
        }


# Создаем глобальный экземпляр для использования в приложении
kb = KnowledgeBase()