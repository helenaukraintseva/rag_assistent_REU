# ai_program.py
from typing import List, Dict, Any
import logging
from api_client import PolzaAIClient

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIKeySelector:
    """Класс для выбора ключа с помощью ИИ"""

    def __init__(self):
        self.client = PolzaAIClient()
        logger.info("AI Key Selector инициализирован")

    def select_key(self, question: str, available_keys: List[str]) -> Dict[str, Any]:
        """Выбирает наиболее подходящий ключ для вопроса"""

        # Создаем промпт для выбора ключа
        keys_list = "\n".join([f"- {key}" for key in available_keys])

        prompt = f"""Ты — интеллектуальный маршрутизатор запросов. Твоя задача — выбрать наиболее подходящий раздел базы знаний для ответа на вопрос пользователя.

Доступные разделы:
{keys_list}

Вопрос пользователя: {question}

Проанализируй вопрос и выбери ОДИН наиболее релевантный раздел из списка выше.
Учитывай:
- Тематику вопроса
- Ключевые слова
- Контекст

Ответь ТОЛЬКО названием раздела (одно слово или фраза из списка выше).
Если ни один раздел не подходит, ответь: "неизвестно"

Раздел:"""

        try:
            response = self.client.generate_content(prompt, max_tokens=50)

            if response and response.strip() in available_keys:
                selected_key = response.strip()
                logger.info(f"Выбран ключ: {selected_key}")
                return {
                    "success": True,
                    "selected_key": selected_key,
                    "confidence": 1.0
                }
            else:
                # Если не удалось выбрать, используем семантический поиск
                return self._fallback_key_selection(question, available_keys)

        except Exception as e:
            logger.error(f"Ошибка при выборе ключа: {e}")
            return self._fallback_key_selection(question, available_keys)

    def _fallback_key_selection(self, question: str, available_keys: List[str]) -> Dict[str, Any]:
        """Запасной метод выбора ключа (простой семантический поиск)"""
        question_lower = question.lower()

        # Простой поиск по ключевым словам
        keyword_scores = {}
        for key in available_keys:
            score = 0
            key_words = key.lower().split()
            for word in key_words:
                if word in question_lower:
                    score += 1
            keyword_scores[key] = score

        if keyword_scores and max(keyword_scores.values()) > 0:
            best_key = max(keyword_scores, key=keyword_scores.get)
            logger.info(f"Fallback: выбран ключ {best_key} с оценкой {keyword_scores[best_key]}")
            return {
                "success": True,
                "selected_key": best_key,
                "confidence": 0.5,
                "method": "fallback"
            }

        return {
            "success": False,
            "selected_key": None,
            "confidence": 0,
            "message": "Не удалось определить релевантный раздел"
        }


class AIGenerator:
    """Класс для генерации ответа с помощью ИИ"""

    def __init__(self):
        self.client = PolzaAIClient()
        logger.info("AI Generator инициализирован")

    def generate_answer(self, question: str, context: str, key: str) -> str:
        """Генерирует ответ на основе контекста"""

        prompt = f"""Ты — AI-ассистент университетской информационной системы. Твоя задача — отвечать на вопросы студентов и сотрудников на основе предоставленной информации.

Информация из раздела "{key}":
{context}

Вопрос пользователя: {question}

Сформулируй четкий, полезный и информативный ответ на основе предоставленной информации.
Если информации недостаточно для полного ответа, укажи это.
Отвечай на том же языке, что и вопрос.
Будь вежливым и helpful.

Не используй звездочки (*) для форматирования.
Пиши простым и понятным языком.

Ответ:"""

        try:
            response = self.client.generate_content(prompt, max_tokens=1000)
            return response if response else "Извините, не удалось сгенерировать ответ."
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            return "Произошла ошибка при генерации ответа. Пожалуйста, попробуйте позже."