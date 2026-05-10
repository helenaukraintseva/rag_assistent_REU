"""
tinyllama_client.py - Клиент для работы с TinyLlama локально
"""

import sys
import os
from typing import Optional, List, Dict, Any


class TinyLlamaClient:
    """Клиент для работы с TinyLlama через llama-cpp-python"""

    def __init__(
            self,
            model_path: str = "./models/tinyllama.gguf",
            n_ctx: int = 2048,
            n_threads: int = 4,
            n_gpu_layers: int = 0,
            verbose: bool = False
    ):
        """
        Инициализация клиента TinyLlama.

        Args:
            model_path: Путь к файлу модели .gguf
            n_ctx: Размер контекстного окна
            n_threads: Количество потоков CPU
            n_gpu_layers: Кол-во слоёв на GPU (0 = только CPU, -1 = все слои)
            verbose: Подробный вывод
        """
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.n_gpu_layers = n_gpu_layers
        self.verbose = verbose
        self._model = None

        # Проверяем существование модели
        if not os.path.exists(model_path):
            print(f"Ошибка: Модель не найдена по пути: {model_path}")
            print("\nСкачайте модель командой:")
            print("  mkdir -p models")
            print("  wget -O models/tinyllama.gguf \\")
            print(
                "    https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf")
            sys.exit(1)

        self._load_model()

    def _load_model(self):
        """Загружает модель llama.cpp"""
        try:
            from llama_cpp import Llama
        except ImportError:
            print("Ошибка: Не установлен llama-cpp-python")
            print("Установите: pip install llama-cpp-python")
            print("\nДля GPU с CUDA:")
            print("  CMAKE_ARGS=\"-DLLAMA_CUDA=on\" pip install llama-cpp-python")
            sys.exit(1)

        if self.verbose:
            print(f"Загрузка модели: {self.model_path}")
            print(f"Контекст: {self.n_ctx}, Потоков: {self.n_threads}, Слоёв GPU: {self.n_gpu_layers}")

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
            print(f"Ошибка загрузки модели: {e}")
            sys.exit(1)

    def _format_chat_prompt(
            self,
            user_message: str,
            system_prompt: Optional[str] = None,
            history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Форматирует сообщения в промпт для TinyLlama.

        TinyLlama использует простой формат без специальных токенов[citation:2].
        """
        prompt_parts = []

        # Системный промпт
        if system_prompt:
            prompt_parts.append(f"System: {system_prompt}\n")

        # История сообщений
        if history:
            for msg in history:
                if msg["role"] == "user":
                    prompt_parts.append(f"User: {msg['content']}\n")
                elif msg["role"] == "assistant":
                    prompt_parts.append(f"Assistant: {msg['content']}\n")

        # Текущий запрос
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
        """
        Отправляет запрос модели и возвращает ответ.

        Args:
            prompt: Текст запроса
            system_prompt: Системный промпт
            history: История диалога
            temperature: Температура (0.0 - 1.0)
            max_tokens: Макс. токенов в ответе
            top_p: Top-p sampling
            repeat_penalty: Штраф за повторения
            stream: Потоковый вывод

        Returns:
            Текст ответа или None
        """
        if self._model is None:
            print("Модель не загружена!")
            return None

        # Форматируем промпт
        formatted_prompt = self._format_chat_prompt(prompt, system_prompt, history)

        if self.verbose:
            print(f"\n--- Промпт ---\n{formatted_prompt}\n--- Конец промпта ---\n")

        try:
            if stream:
                # Потоковая генерация
                full_response = ""
                print("\n🤖 ", end="", flush=True)
                for chunk in self._model(
                        formatted_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        top_p=top_p,
                        repeat_penalty=repeat_penalty,
                        stream=True
                ):
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        token = chunk["choices"][0].get("text", "")
                        if token:
                            print(token, end="", flush=True)
                            full_response += token
                print("\n")
                return full_response
            else:
                # Обычная генерация
                response = self._model(
                    formatted_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    repeat_penalty=repeat_penalty
                )
                return response["choices"][0]["text"].strip()

        except Exception as e:
            print(f"Ошибка генерации: {e}")
            return None

    def chat(self) -> None:
        """Интерактивный режим чата"""
        print("\n" + "=" * 50)
        print("🤖 TinyLlama Chat - интерактивный режим")
        print("=" * 50)
        print("Команды: /exit - выход, /clear - очистить историю, /temp X - изменить температуру")
        print("=" * 50 + "\n")

        history = []
        current_temp = 0.7

        while True:
            try:
                user_input = input("\n👤 Вы: ").strip()

                if not user_input:
                    continue

                if user_input.lower() == "/exit":
                    print("До свидания!")
                    break
                elif user_input.lower() == "/clear":
                    history = []
                    print("История очищена.")
                    continue
                elif user_input.lower().startswith("/temp"):
                    parts = user_input.split()
                    if len(parts) == 2:
                        try:
                            current_temp = float(parts[1])
                            print(f"Температура установлена на {current_temp}")
                        except ValueError:
                            print("Ошибка: введите число (0.0 - 1.0)")
                    else:
                        print(f"Текущая температура: {current_temp}")
                    continue

                # Отправляем запрос
                response = self.process_prompt(
                    prompt=user_input,
                    history=history,
                    temperature=current_temp,
                    stream=True
                )

                if response:
                    # Сохраняем в историю
                    history.append({"role": "user", "content": user_input})
                    history.append({"role": "assistant", "content": response})

                    # Ограничиваем историю (последние 10 сообщений)
                    if len(history) > 10:
                        history = history[-10:]

            except KeyboardInterrupt:
                print("\n\nДо свидания!")
                break
            except Exception as e:
                print(f"Ошибка: {e}")

    def get_model_info(self) -> Dict[str, Any]:
        """Информация о модели"""
        return {
            "model_path": self.model_path,
            "context_size": self.n_ctx,
            "threads": self.n_threads,
            "gpu_layers": self.n_gpu_layers,
            "is_loaded": self._model is not None
        }


# --- Быстрые функции для простого использования ---

def quick_ask(
        prompt: str,
        model_path: str = "./models/tinyllama.gguf",
        **kwargs
) -> Optional[str]:
    """
    Быстрый одноразовый запрос.

    Args:
        prompt: Текст запроса
        model_path: Путь к модели
        **kwargs: temperature, max_tokens, etc.

    Returns:
        Ответ модели
    """
    client = TinyLlamaClient(model_path, verbose=False)
    return client.process_prompt(prompt, **kwargs)


# --- Примеры использования ---

if __name__ == "__main__":
    print("=" * 60)
    print("TinyLlama Client - Локальная работа без интернета")
    print("=" * 60)

    # Создание клиента
    client = TinyLlamaClient(
        model_path="./models/tinyllama.gguf",
        n_ctx=2048,  # Размер контекста
        n_threads=4,  # Количество потоков CPU
        n_gpu_layers=0,  # 0 = только CPU, -1 = все слои на GPU
        verbose=True
    )

    print("\n📋 Информация о модели:")
    for key, value in client.get_model_info().items():
        print(f"   {key}: {value}")

    # Пример 1: Простой запрос
    print("\n" + "=" * 50)
    print("Пример 1: Простой запрос")
    print("=" * 50)

    response = client.process_prompt(
        prompt="Расскажи шутку про программистов",
        temperature=0.7,
        max_tokens=256
    )
    if response:
        print(f"\n🤖 Ответ:\n{response}")

    # Пример 2: С системным промптом
    print("\n" + "=" * 50)
    print("Пример 2: С системным промптом")
    print("=" * 50)

    response = client.process_prompt(
        prompt="Что такое Python?",
        system_prompt="Ты — эксперт по Python, отвечай кратко и с примерами кода.",
        temperature=0.5,
        max_tokens=256
    )
    if response:
        print(f"\n🤖 Ответ:\n{response}")

    # Пример 3: С историей диалога
    print("\n" + "=" * 50)
    print("Пример 3: Диалог с историей")
    print("=" * 50)

    history = [
        {"role": "user", "content": "Меня зовут Александр"},
        {"role": "assistant", "content": "Приятно познакомиться, Александр! Чем я могу помочь?"}
    ]

    response = client.process_prompt(
        prompt="Как меня зовут?",
        history=history,
        temperature=0.5,
        max_tokens=128
    )
    if response:
        print(f"\n🤖 Ответ:\n{response}")

    # Пример 4: Интерактивный чат
    print("\n" + "=" * 50)
    print("Пример 4: Интерактивный режим")
    print("=" * 50)

    run_chat = input("\nЗапустить интерактивный чат? (y/n): ").lower()
    if run_chat == 'y':
        client.chat()