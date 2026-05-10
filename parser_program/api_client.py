import requests
import json
from typing import Dict, Any, Optional

from config import settings


class PolzaAIClient:
    """Клиент для работы с Polza.ai API"""

    def __init__(self):
        self.api_key = settings.POLZA_API_KEY
        self.base_url = settings.POLZA_API_URL
        self.model = settings.POLZA_MODEL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def generate_content(self, prompt: str, max_tokens: int = 2000) -> Optional[str]:
        """
        Генерирует контент через Polza.ai API

        Args:
            prompt: Текст промпта для генерации
            max_tokens: Максимальное количество токенов в ответе

        Returns:
            Сгенерированный текст или None в случае ошибки
        """
        try:
            # Подготовка данных для запроса
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7
            }

            # Отправка запроса
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )

            # Проверка ответа
            if response.status_code == 200 or response.status_code == 201:
                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # Очистка контента от лишних символов
                cleaned_content = self._clean_content(content)
                return cleaned_content
            else:
                print(f"Ошибка API: {response.status_code}")
                print(f"Ответ: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе к API: {e}")
            return None
        except (KeyError, IndexError) as e:
            print(f"Ошибка при обработке ответа API: {e}")
            return None

    def _clean_content(self, content: str) -> str:
        """
        Очищает контент от лишних символов (*, лишние форматирования)

        Args:
            content: Исходный текст

        Returns:
            Очищенный текст
        """
        # Удаляем звездочки в начале строк и вокруг текста
        lines = content.split('\n')
        cleaned_lines = []

        for line in lines:
            # Удаляем звездочки в начале строки
            line = line.strip()
            if line.startswith('*') and line.endswith('*'):
                line = line[1:-1].strip()
            elif line.startswith('*'):
                line = line[1:].strip()
            elif line.endswith('*'):
                line = line[:-1].strip()

            # Удаляем двойные звездочки
            line = line.replace('**', '')

            # Удаляем лишние пробелы
            line = ' '.join(line.split())

            if line:  # Добавляем только непустые строки
                cleaned_lines.append(line)

        # Собираем обратно в текст
        cleaned_content = '\n'.join(cleaned_lines)

        # Удаляем повторяющиеся пустые строки
        while '\n\n\n' in cleaned_content:
            cleaned_content = cleaned_content.replace('\n\n\n', '\n\n')

        return cleaned_content.strip()