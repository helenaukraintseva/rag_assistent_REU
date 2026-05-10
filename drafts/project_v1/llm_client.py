"""
Клиент для работы с LLM API.
ИИ получает ТОЛЬКО КЛЮЧИ (названия документов/разделов) из базы знаний.
Формирование ответа происходит на основе содержимого, но содержимое НЕ отправляется в ИИ.
"""

import requests
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from config import POLZA_API_KEY, POLZA_API_URL, POLZA_MODEL
from knowledge_base import kb

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Клиент для работы с LLM.
    Получает от системы только ключи, генерирует ответ на основе своего понимания,
    но с жестким ограничением: ответ должен базироваться на документах,
    соответствующих этим ключам.
    """

    def __init__(self):
        self.api_key = POLZA_API_KEY
        self.base_url = POLZA_API_URL
        self.model = POLZA_MODEL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def create_key_based_prompt(self, question: str, relevant_keys: List[Dict[str, Any]]) -> str:
        """
        Создание промпта, который содержит ТОЛЬКО КЛЮЧИ, а не содержимое.
        """
        # Форматируем информацию о ключах (без содержимого)
        keys_info = []
        for key_data in relevant_keys:
            keys_info.append(
                f"- КЛЮЧ: '{key_data['key']}' | "
                f"Название: {key_data['title']} | "
                f"Категория: {key_data['category']} | "
                f"Ключевые слова: {', '.join(key_data['keywords'][:5])}"
            )

        keys_text = "\n".join(keys_info)

        prompt = f"""# ЗАДАЧА: ОТВЕТ НА ВОПРОЗ НА ОСНОВЕ КЛЮЧЕЙ ДОКУМЕНТОВ

## ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{question}

## ДОСТУПНЫЕ КЛЮЧИ ДОКУМЕНТОВ (ТОЛЬКО НАЗВАНИЯ):
{keys_text}

## ВАЖНЫЕ ИНСТРУКЦИИ:
1. У тебя нет доступа к содержимому документов — только к их ключам/названиям.
2. Ты должен предположить, какая информация содержится в документах, основываясь на их ключах.
3. Твой ответ должен быть общим и информативным, но ты должен указать, что информация основана на предположении из названий документов.
4. НЕ придумывай конкретных деталей, которых нет в ключах.
5. Если ключи не позволяют ответить на вопрос, скажи об этом честно.

## ФОРМАТ ОТВЕТА:
1. Краткий ответ на основе доступных ключей
2. Указание, какие именно документы (ключи) были использованы
3. Рекомендация обратиться к полному тексту документов для деталей

## ОТВЕТ (на русском языке):
"""
        return prompt

    def generate_response(self, prompt: str, max_tokens: int = 1000) -> Optional[str]:
        """Генерация ответа через API Polza.ai"""
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Ты - ассистент учебного офиса, который помогает студентам находить информацию. Ты видишь только ключи/названия документов, но не их содержимое. Отвечай на основе этих ключей, но не придумывай деталей, которых нет в ключах."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3  # Низкая температура для более детерминированных ответов
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return self._clean_response(content)
            else:
                logger.error(f"Ошибка API: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Ошибка при генерации ответа: {e}")
            return None

    def _clean_response(self, content: str) -> str:
        """Очистка ответа от лишних символов"""
        # Удаляем маркдаун-форматирование, если нужно
        lines = content.split('\n')
        cleaned = []
        for line in lines:
            line = line.strip()
            # Удаляем символы маркдауна, если они мешают
            line = line.replace('#', '').replace('*', '').strip()
            if line:
                cleaned.append(line)
        return '\n'.join(cleaned)

    def get_answer(self, question: str, relevant_keys: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Основной метод: получение ответа на основе ключей.
        """
        if not relevant_keys:
            return {
                "success": False,
                "answer": "Не найдено релевантных документов для ответа на вопрос.",
                "sources": [],
                "keys_used": []
            }

        try:
            # Создаем промпт с ключами
            prompt = self.create_key_based_prompt(question, relevant_keys)

            # Получаем ответ от LLM
            llm_response = self.generate_response(prompt)

            if llm_response:
                # Формируем результат
                keys_used = [key_data['key'] for key_data in relevant_keys]

                return {
                    "success": True,
                    "answer": llm_response,
                    "sources": keys_used,  # Это ключи, которые использовались
                    "keys_used": keys_used,
                    "key_details": relevant_keys,  # Детальная информация о ключах
                    "note": "Ответ основан на названиях документов. Для точной информации обратитесь к полным текстам."
                }
            else:
                # Fallback - если LLM не ответил, возвращаем информацию о ключах
                return self._create_key_based_fallback(question, relevant_keys)

        except Exception as e:
            logger.error(f"Ошибка в get_answer: {e}")
            return {
                "success": False,
                "answer": f"Ошибка при обработке запроса: {str(e)}",
                "sources": [key_data['key'] for key_data in relevant_keys],
                "keys_used": [key_data['key'] for key_data in relevant_keys],
                "error": str(e)
            }

    def _create_key_based_fallback(self, question: str, relevant_keys: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Создание fallback-ответа на основе только ключей (без LLM).
        """
        response_parts = [
            f"## Вопрос: {question}",
            "\n### Найдены следующие документы, которые могут содержать ответ:"
        ]

        for key_data in relevant_keys:
            response_parts.append(
                f"\n**📄 {key_data['title']}**\n"
                f"   Ключ: `{key_data['key']}`\n"
                f"   Категория: {key_data['category']}\n"
                f"   Ключевые слова: {', '.join(key_data['keywords'][:5])}"
            )

        response_parts.append(
            "\n---\n"
            "⚠️ *Примечание: Сервис генерации временно недоступен. "
            "Обратитесь к полным текстам документов для получения точной информации.*"
        )

        return {
            "success": True,
            "answer": "\n".join(response_parts),
            "sources": [key_data['key'] for key_data in relevant_keys],
            "keys_used": [key_data['key'] for key_data in relevant_keys],
            "key_details": relevant_keys,
            "note": "LLM недоступен, показаны только ключи документов"
        }


# Создаем глобальный экземпляр
llm_client = LLMClient()