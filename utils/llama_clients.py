# llama_clients.py
import logging
from typing import Dict, Any, List, Optional
import os
import sys

logger = logging.getLogger(__name__)


class TinyLlamaClient:
    """Клиент для работы с TinyLlama локально"""

    def __init__(
            self,
            model_path: str = "./models/tinyllama.gguf",
            n_ctx: int = 2048,
            n_threads: int = 4,
            n_gpu_layers: int = 0,
            verbose: bool = False
    ):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.n_gpu_layers = n_gpu_layers
        self.verbose = verbose
        self._model = None

        # Проверяем существование модели
        if not os.path.exists(model_path):
            logger.warning(f"Модель не найдена: {model_path}")
            self._model = None
        else:
            self._load_model()

    def _load_model(self):
        """Загружает модель llama.cpp"""
        try:
            from llama_cpp import Llama
        except ImportError:
            logger.error("llama-cpp-python не установлен")
            print("\nУстановите: pip install llama-cpp-python")
            self._model = None
            return

        if self.verbose:
            print(f"Загрузка модели: {self.model_path}")

        try:
            self._model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_gpu_layers=self.n_gpu_layers,
                verbose=self.verbose
            )
            if self.verbose:
                print("Модель успешно загружена!")
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            self._model = None

    def _format_chat_prompt(self, user_message: str, system_prompt: Optional[str] = None,
                            history: Optional[List[Dict[str, str]]] = None) -> str:
        """Форматирует сообщения в промпт для TinyLlama"""
        prompt_parts = []

        if system_prompt:
            prompt_parts.append(f"System: {system_prompt}\n")

        if history:
            for msg in history:
                if msg["role"] == "user":
                    prompt_parts.append(f"User: {msg['content']}\n")
                elif msg["role"] == "assistant":
                    prompt_parts.append(f"Assistant: {msg['content']}\n")

        prompt_parts.append(f"User: {user_message}\n")
        prompt_parts.append("Assistant: ")

        return "".join(prompt_parts)

    def process_prompt(
            self,
            prompt: str,
            system_prompt: Optional[str] = None,
            history: Optional[List[Dict[str, str]]] = None,
            temperature: float = 0.7,
            max_tokens: int = 512,
            top_p: float = 0.95,
            repeat_penalty: float = 1.1,
            stream: bool = False
    ) -> Optional[str]:
        """Отправляет запрос модели и возвращает ответ"""

        if self._model is None:
            logger.warning("Модель не загружена, возвращаем заглушку")
            return self._get_mock_response(prompt)

        # Форматируем промпт
        formatted_prompt = self._format_chat_prompt(prompt, system_prompt, history)

        try:
            response = self._model(
                formatted_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                repeat_penalty=repeat_penalty
            )
            return response["choices"][0]["text"].strip()
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
            return self._get_mock_response(prompt)

    def _get_mock_response(self, prompt: str) -> str:
        """Возвращает тестовый ответ если модель не загружена"""
        prompt_lower = prompt.lower()

        if "выбери" in prompt_lower or "раздел" in prompt_lower:
            if "стипендия" in prompt_lower:
                return "стипендии"
            elif "общежитие" in prompt_lower:
                return "общежитие"
            elif "сессия" in prompt_lower:
                return "сессия"
            else:
                return "неизвестно"

        return "Это ответ от TinyLlama (локальный режим). Для работы установите модель."


class KeySelector:
    """Класс для выбора ключа (раздела) с помощью TinyLlama"""

    def __init__(self, client: TinyLlamaClient, knowledge_base: Dict):
        from api_client import PolzaAIClient
        self.client = PolzaAIClient()
        self.knowledge_base = knowledge_base
        logger.info("KeySelector (TinyLlama) инициализирован")

    def select_key(self, question: str, available_keys: List[str]) -> Dict[str, Any]:
        """Выбирает наиболее подходящий раздел"""

        if not available_keys:
            return {"success": False, "selected_key": None, "doc_link": ""}

        # Создаем промпт для выбора ключа
        keys_list = "\n".join([f"- {key}" for key in available_keys])

        prompt = f"""Ты — интеллектуальный маршрутизатор запросов. Выбери наиболее подходящий раздел для ответа на вопрос.

Доступные разделы:
{keys_list}

Вопрос: {question}

Ответь ТОЛЬКО названием раздела из списка выше.
Если ни один не подходит, ответь: "неизвестно"

Раздел:"""

        try:
            response = self.client.generate_content(
                prompt=prompt,
                max_tokens=50
            )

            if response:
                response = response.strip().lower()
                for key in available_keys:
                    if key.lower() == response or key.lower() in response or response in key.lower():
                        return {
                            "success": True,
                            "selected_key": key,
                            "confidence": 0.9,
                            "method": "ai",
                            "doc_link": self.knowledge_base.get(key, {}).get('doc_link', '')
                        }

            # Fallback
            return self._fallback_selection(question, available_keys)

        except Exception as e:
            logger.error(f"Ошибка выбора ключа: {e}")
            return self._fallback_selection(question, available_keys)

    def _fallback_selection(self, question: str, available_keys: List[str]) -> Dict[str, Any]:
        """Простой поиск по ключевым словам"""
        question_lower = question.lower()

        for key in available_keys:
            key_words = key.lower().split()
            if any(word in question_lower for word in key_words):
                return {
                    "success": True,
                    "selected_key": key,
                    "confidence": 0.5,
                    "method": "fallback",
                    "doc_link": self.knowledge_base.get(key, {}).get('doc_link', '')
                }

        return {
            "success": False,
            "selected_key": None,
            "confidence": 0,
            "message": "Не удалось определить раздел",
            "doc_link": ""
        }


class AnswerGenerator:
    """Класс для генерации ответов с помощью TinyLlama"""

    def __init__(self, client: TinyLlamaClient):
        self.client = client
        logger.info("AnswerGenerator (TinyLlama) инициализирован")

    def generate_answer(self, question: str, context: str, key: str, doc_link: str = "") -> str:
        """Генерирует ответ на основе контекста"""

        # Добавляем информацию о ссылке
        link_text = f"\n\nИсточник: {doc_link}" if doc_link else ""

        prompt = f"""Ты — AI-ассистент университетской информационной системы. Отвечай на вопросы студентов на основе предоставленной информации.

Информация из раздела "{key}":
{context}
{link_text}

Вопрос пользователя: {question}

Дай четкий и полезный ответ на основе информации выше.
Если информации недостаточно, скажи об этом.
Отвечай на том же языке, что и вопрос.
Будь вежливым и helpful.
Не используй звездочки для форматирования.

Ответ:"""

        try:
            response = self.client.process_prompt(
                prompt=prompt,
                temperature=0.7,
                max_tokens=512
            )
            return response if response else "Извините, не удалось сгенерировать ответ."
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            return "Произошла ошибка при генерации ответа."


def create_llama_clients(
        knowledge_base: Dict,
        model_path: str = "./models/tinyllama.gguf",
        n_ctx: int = 2048,
        n_threads: int = 4,
        n_gpu_layers: int = 0,
        verbose: bool = False
) -> Dict[str, Any]:
    """
    Фабричная функция для создания клиентов TinyLlama

    Args:
        knowledge_base: база знаний
        model_path: путь к модели .gguf
        n_ctx: размер контекста
        n_threads: количество потоков CPU
        n_gpu_layers: количество слоев на GPU
        verbose: подробный вывод

    Returns:
        словарь с клиентами
    """

    # Создаем двух независимых клиентов
    client_1 = TinyLlamaClient(
        model_path=model_path,
        n_ctx=n_ctx,
        n_threads=n_threads,
        n_gpu_layers=n_gpu_layers,
        verbose=verbose
    )

    client_2 = TinyLlamaClient(
        model_path=model_path,
        n_ctx=n_ctx,
        n_threads=n_threads,
        n_gpu_layers=n_gpu_layers,
        verbose=verbose
    )

    return {
        "retriever": KeySelector(client_1, knowledge_base),
        "answer_generator": AnswerGenerator(client_2),

    }