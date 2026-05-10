"""
ollama_tinyllama_client.py - Клиент для TinyLlama через Ollama
Работает полностью локально, без интернета после установки модели
"""

import ollama
from typing import Optional, List, Dict, Any
import json


class OllamaTinyLlama:
    """
    Клиент для работы с TinyLlama через Ollama.
    Проще, чем llama-cpp-python, и без проблем с установкой!
    """

    def __init__(
            self,
            model_name: str = "tinyllama",
            host: str = "http://localhost:11434",
            verbose: bool = True
    ):
        """
        Инициализация клиента.

        Args:
            model_name: Имя модели (tinyllama, llama3, mistral и др.)
            host: Адрес сервера Ollama
            verbose: Подробный вывод
        """
        self.model_name = model_name
        self.host = host
        self.verbose = verbose

        # Настройка подключения к Ollama
        ollama.Client(host=host)

        # Проверяем, что модель загружена
        self._check_model()

    def _check_model(self):
        """Проверяет, что модель доступна"""
        try:
            models = ollama.list()
            model_names = [m['model'] for m in models.get('models', [])]

            # Проверяем, есть ли наша модель (с игнорированием тегов)
            model_available = False
            for m in model_names:
                if m.startswith(self.model_name):
                    model_available = True
                    break

            if not model_available:
                print(f"⚠️ Модель '{self.model_name}' не найдена!")
                print(f"Скачайте её командой: ollama pull {self.model_name}")
            elif self.verbose:
                print(f"✅ Модель '{self.model_name}' готова к работе")

        except Exception as e:
            print(f"❌ Ошибка подключения к Ollama: {e}")
            print("Убедитесь, что Ollama установлен и запущен")

    def process_prompt(
            self,
            prompt: str,
            system_prompt: Optional[str] = None,
            history: Optional[List[Dict[str, str]]] = None,
            temperature: float = 0.7,
            max_tokens: int = 512,
            top_p: float = 0.9,
            stream: bool = False
    ) -> Optional[str]:
        """
        Отправляет запрос модели и возвращает ответ.

        Args:
            prompt: Текст запроса пользователя
            system_prompt: Системный промпт
            history: История диалога
            temperature: Температура (0.0 - 1.0)
            max_tokens: Максимум токенов в ответе
            top_p: Top-p sampling
            stream: Потоковый вывод

        Returns:
            Текст ответа или None
        """
        # Формируем сообщения
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": prompt})

        # Параметры запроса
        options = {
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": max_tokens,
        }

        try:
            if stream:
                # Потоковая генерация
                print("🤖 ", end="", flush=True)

                stream_response = ollama.chat(
                    model=self.model_name,
                    messages=messages,
                    options=options,
                    stream=True
                )

                full_response = ""
                for chunk in stream_response:
                    if 'message' in chunk and 'content' in chunk['message']:
                        token = chunk['message']['content']
                        print(token, end="", flush=True)
                        full_response += token

                print()  # Новая строка
                return full_response
            else:
                # Обычная генерация
                response = ollama.chat(
                    model=self.model_name,
                    messages=messages,
                    options=options
                )

                return response['message']['content']

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None

    def chat(self):
        """Интерактивный режим чата"""
        print("\n" + "=" * 60)
        print(f"🤖 TinyLlama Chat (через Ollama)")
        print("=" * 60)
        print("Команды:")
        print("  /exit    - выход")
        print("  /clear   - очистить историю")
        print("  /temp X  - изменить температуру")
        print("=" * 60 + "\n")

        history = []
        current_temp = 0.7

        while True:
            try:
                user_input = input("👤 Вы: ").strip()

                if not user_input:
                    continue

                if user_input.lower() == "/exit":
                    print("👋 До свидания!")
                    break
                elif user_input.lower() == "/clear":
                    history = []
                    print("🗑️ История очищена.")
                    continue
                elif user_input.lower().startswith("/temp"):
                    parts = user_input.split()
                    if len(parts) == 2:
                        try:
                            current_temp = float(parts[1])
                            print(f"🌡️ Температура: {current_temp}")
                        except ValueError:
                            print("Ошибка: введите число 0.0-1.0")
                    continue

                response = self.process_prompt(
                    prompt=user_input,
                    history=history,
                    temperature=current_temp,
                    stream=True
                )

                if response:
                    history.append({"role": "user", "content": user_input})
                    history.append({"role": "assistant", "content": response})

                    # Ограничиваем историю (последние 20 сообщений = 10 диалогов)
                    if len(history) > 20:
                        history = history[-20:]

            except KeyboardInterrupt:
                print("\n\n👋 До свидания!")
                break
            except Exception as e:
                print(f"❌ Ошибка: {e}")

    def get_model_info(self) -> Dict[str, Any]:
        """Информация о модели"""
        try:
            model_info = ollama.show(self.model_name)
            return {
                "model": self.model_name,
                "modelfile": model_info.get('modelfile', 'N/A'),
                "parameters": model_info.get('parameters', 'N/A'),
                "template": model_info.get('template', 'N/A'),
            }
        except:
            return {
                "model": self.model_name,
                "status": "Модель не найдена, выполните: ollama pull " + self.model_name
            }


def quick_ask(prompt: str, model: str = "tinyllama", **kwargs) -> Optional[str]:
    """
    Быстрая функция для одноразового запроса.

    Args:
        prompt: Текст запроса
        model: Имя модели (tinyllama, llama3, mistral, и т.д.)
        **kwargs: temperature, max_tokens и др.

    Returns:
        Ответ модели
    """
    client = OllamaTinyLlama(model_name=model, verbose=False)
    return client.process_prompt(prompt, **kwargs)


# --- Примеры использования ---

if __name__ == "__main__":
    print("=" * 60)
    print("TinyLlama через Ollama - полная локальная работа")
    print("=" * 60)

    # Создаём клиент
    client = OllamaTinyLlama(model_name="tinyllama", verbose=True)

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
        print(f"\n🤖 Ответ:\n{response}\n")

    # Пример 2: С системным промптом
    print("\n" + "=" * 50)
    print("Пример 2: Специализированный ответ")
    print("=" * 50)

    response = client.process_prompt(
        prompt="Что такое API простыми словами?",
        system_prompt="Ты — преподаватель для начинающих, объясняй максимально просто, используй аналогии.",
        temperature=0.5,
        max_tokens=256
    )
    if response:
        print(f"\n🤖 Ответ:\n{response}\n")

    # Пример 3: Диалог с историей
    print("\n" + "=" * 50)
    print("Пример 3: Диалог с памятью")
    print("=" * 50)

    history = [
        {"role": "user", "content": "Меня зовут Александр, я учусь программировать."},
        {"role": "assistant",
         "content": "Привет, Александр! Отлично, что ты решил научиться программированию. Чем я могу помочь?"}
    ]

    response = client.process_prompt(
        prompt="Напомни, как меня зовут и что я изучаю?",
        history=history,
        temperature=0.5,
        max_tokens=128
    )
    if response:
        print(f"🤖 Ответ:\n{response}\n")

    # Пример 4: Интерактивный чат
    print("=" * 50)
    print("Пример 4: Интерактивный режим")
    print("=" * 50)

    run_chat = input("\nЗапустить полноценный чат? (y/n): ").lower()
    if run_chat == 'y':
        client.chat()