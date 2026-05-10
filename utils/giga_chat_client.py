"""
GigaChat API клиент для отправки запросов к модели.
Использование:
    from gigachat_client import GigaChatClient

    client = GigaChatClient(auth_key="ваш_ключ")
    response = client.process_prompt("Ваш вопрос")
"""

import requests
import uuid
import json
from typing import Optional, List, Dict, Any

# Базовые URL
AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"


class GigaChatClient:
    """Клиент для работы с GigaChat API"""

    def __init__(
        self,
        auth_key: str,
        scope: str = "GIGACHAT_API_PERS",
        verify_ssl: bool = False,
        model: str = "GigaChat:latest"
    ):
        """
        Инициализация клиента GigaChat.

        Args:
            auth_key: Ключ авторизации из кабинета разработчика
            scope: Сфера доступа (по умолчанию для физических лиц)
            verify_ssl: Проверять ли SSL сертификаты (для продакшена - True)
            model: Модель по умолчанию
        """
        self.auth_key = auth_key
        self.scope = scope
        self.verify_ssl = verify_ssl
        self.model = model
        self._access_token = None

    def _get_access_token(self) -> str:
        """Получает access token для авторизации запросов."""
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'RqUID': str(uuid.uuid4()),
            'Authorization': f'Basic {self.auth_key}'
        }
        payload = {'scope': self.scope}

        try:
            response = requests.post(
                AUTH_URL,
                headers=headers,
                data=payload,
                timeout=30,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            token_data = response.json()
            self._access_token = token_data['access_token']
            return self._access_token
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении токена: {e}")
            if hasattr(response, 'status_code') and response.status_code == 401:
                print("Неверный авторизационный ключ.")
            raise
        except KeyError:
            print("Ошибка: 'access_token' не найден в ответе от сервера.")
            if hasattr(response, 'text'):
                print(f"Полный ответ сервера: {response.text}")
            raise

    def process_prompt(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Optional[str]:
        """
        Отправляет промпт в GigaChat и возвращает ответ модели.

        Args:
            prompt: Текст запроса пользователя
            model: Имя модели (если не указано, используется из инициализации)
            temperature: Температура генерации (0.0 - 1.0)
            max_tokens: Максимальное количество токенов в ответе
            system_prompt: Системный промпт для задания контекста
            history: История предыдущих сообщений в формате [{"role": "user", "content": "..."}, ...]

        Returns:
            Текст ответа ассистента или None в случае ошибки
        """
        # Шаг 1: Получение токена доступа
        try:
            access_token = self._get_access_token()
        except Exception:
            print("Не удалось получить access token. Функция остановлена.")
            return None

        # Шаг 2: Формирование сообщений
        messages = []

        # Добавляем системный промпт если указан
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Добавляем историю если есть
        if history:
            messages.extend(history)

        # Добавляем текущий запрос
        messages.append({"role": "user", "content": prompt})

        # Шаг 3: Формирование запроса
        url = API_URL
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }

        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Шаг 4: Отправка запроса
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=60,
                verify=self.verify_ssl
            )
            response.raise_for_status()

            response_data = response.json()
            assistant_message = response_data['choices'][0]['message']['content']
            return assistant_message

        except requests.exceptions.Timeout:
            print("Ошибка: Таймаут при обращении к API.")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе к GigaChat API: {e}")
            if hasattr(response, 'status_code'):
                if response.status_code == 401:
                    print("Истек или недействителен токен доступа.")
                elif response.status_code == 429:
                    print("Превышен лимит запросов.")
                else:
                    print(f"Код ошибки: {response.status_code}")
                    print(f"Тело ответа: {response.text}")
            return None
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"Ошибка при разборе ответа от сервера: {e}")
            if hasattr(response, 'text'):
                print(f"Ответ сервера: {response.text}")
            return None

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512
    ) -> Optional[str]:
        """
        Отправляет готовый список сообщений в GigaChat.

        Args:
            messages: Список сообщений в формате [{"role": "user", "content": "..."}, ...]
            model: Имя модели
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов

        Returns:
            Текст ответа ассистента или None
        """
        try:
            access_token = self._get_access_token()
        except Exception:
            print("Не удалось получить access token.")
            return None

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }

        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            response = requests.post(
                API_URL,
                headers=headers,
                json=payload,
                timeout=60,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            response_data = response.json()
            return response_data['choices'][0]['message']['content']
        except Exception as e:
            print(f"Ошибка при запросе: {e}")
            return None


# --- Упрощенная функция для быстрого использования ---
def quick_ask(prompt: str, auth_key: str, **kwargs) -> Optional[str]:
    """
    Быстрая функция для одноразового запроса к GigaChat.

    Args:
        prompt: Текст запроса
        auth_key: Ключ авторизации
        **kwargs: Дополнительные параметры (temperature, max_tokens, model и т.д.)

    Returns:
        Текст ответа или None
    """
    client = GigaChatClient(auth_key)
    return client.process_prompt(prompt, **kwargs)


# --- Пример использования (только для тестирования модуля) ---
if __name__ == "__main__":
    # Этот блок выполняется только при запуске файла напрямую
    # При импорте модуля этот код не выполняется

    from config import MY_AUTH_KEY

    # Пример 1: Использование класса
    client = GigaChatClient(auth_key=MY_AUTH_KEY)

    user_prompt = "Объясни, как работает квантовая запутанность, простыми словами."
    print(f"Отправляем промпт: '{user_prompt}'\n")

    result = client.process_prompt(user_prompt)
    if result:
        print("--- Ответ от GigaChat ---")
        print(result)
    else:
        print("Не удалось получить ответ от модели.")

    # Пример 2: С системным промптом
    print("\n" + "="*50 + "\n")
    print("Пример с системным промптом:")
    result_with_system = client.process_prompt(
        prompt="Что такое Python?",
        system_prompt="Ты - эксперт по Python, отвечай кратко и по делу."
    )
    if result_with_system:
        print(result_with_system)