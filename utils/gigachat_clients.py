# gigachat_clients.py
import logging
from typing import Dict, Any, List, Optional
import requests
from giga_chat_client import GigaChatClient as BaseGigaChatClient

logger = logging.getLogger(__name__)


class KeySelector:
    """Класс для выбора ключа (раздела)"""

    def __init__(self, client, knowledge_base: Dict):
        from api_client import PolzaAIClient
        self.client = PolzaAIClient()
        self.knowledge_base = knowledge_base

    def select_key(self, question: str, available_keys: List[str]) -> Dict[str, Any]:
        """Выбирает подходящий раздел"""
        keys_list = "\n".join([f"- {key}" for key in available_keys])

        prompt = f"""Выбери наиболее подходящий раздел для вопроса (сверяй по описанию desc).
Доступные разделы:
{keys_list}
Вопрос: {question}
Ответь ТОЛЬКО названием раздела (без описания). Если не подходит - ответь только "неизвестно" (больше ничего писать не нужно)
Раздел:"""
        try:
            response = self.client.generate_content(
                prompt=prompt,
                max_tokens=200
            )

            if response:
                return {
                    "success": True,
                    "selected_key": response
                }

            # Простой fallback
            return self._fallback(question, available_keys)
        except:
            return self._fallback(question, available_keys)

    def _fallback(self, question: str, available_keys: List[str]) -> Dict[str, Any]:
        """Простой поиск по ключевым словам"""
        question_lower = question.lower()
        for key in available_keys:
            if any(word in question_lower for word in key.lower().split()):
                return {
                    "success": True,
                    "selected_key": key,
                    "doc_link": self.knowledge_base.get(key, {}).get('doc_link', '')
                }

        return {"success": False, "selected_key": None, "doc_link": ""}


class AnswerGenerator:
    """Класс для генерации ответов"""

    def __init__(self, client: BaseGigaChatClient):
        self.client = client

    def generate_answer(self, question: str, context: str, key: str, doc_link: str = "") -> str:
        """Генерирует ответ на основе контекста"""
        system_prompt = """Ты - полезный ассистент, который отвечает на вопросы строго на основе предоставленной информации.
Не используй свои знания, отвечай только из контекста.
Если информация неполная, скажи об этом честно."""

        user_prompt = f"""Информация:
{context}

Вопрос: {question}

Пожалуйста, ответь на вопрос, используя только предоставленную информацию."""
        # from api_client import PolzaAIClient
        # self.client = PolzaAIClient()
        # response = self.client.generate_content(
        #     prompt=user_prompt,
        #     max_tokens=2000,
        # )
        try:
            response = self.client.process_prompt(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=1000,
                temperature=0.4
            )

            return response if response else "Не удалось сгенерировать ответ."
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа: {e}")
            return "Ошибка генерации ответа."


def create_gigachat_clients(auth_key: str, scope: str, knowledge_base: Dict):
    """Фабрика для создания клиентов GigaChat"""
    # Создаем клиент на основе готового модуля
    client = BaseGigaChatClient(
        auth_key=auth_key,
        scope=scope,
        verify_ssl=False,  # Для разработки, в продакшене лучше True
        model="GigaChat:latest"
    )

    return {
        "retriever": KeySelector(client, knowledge_base),
        "answer_generator": AnswerGenerator(client)
    }