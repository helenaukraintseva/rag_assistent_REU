import requests
import json
from typing import Dict, Any, Optional
from config import POLZA_API_KEY, POLZA_API_URL, POLZA_MODEL


class PolzaAIClient:
    def __init__(self):
        self.api_key = POLZA_API_KEY
        self.base_url = POLZA_API_URL
        self.model = POLZA_MODEL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def generate_content(self, prompt: str, max_tokens: int = 2000) -> Optional[str]:
        """Генерирует контент через Polza.ai API"""
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
        """Очищает контент от лишних символов (*, лишние форматирования)"""
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

    def create_content_prompt(self, user_prompt: str, theme: str, style: str) -> str:
        """Создает промпт для генерации контента"""
        base_prompt = f"""Ты — профессиональный копирайтер и контент-менеджер.
Тематика: {theme}
Стилистика: {style}

Задача пользователя: {user_prompt}

Создай качественный контент, соответствующий тематике и стилистике.
Контент должен быть:
1. Практичным и полезным
2. Соответствующим стилю {style}
3. Легким для чтения и восприятия
4. Без лишних формальностей

Не используй звездочки (*) для форматирования.
Не добавляй лишние символы оформления.
Пиши простым и понятным языком.

Контент:"""

        return base_prompt

    def create_content_plan_prompt(self, theme: str, style: str) -> str:
        """Создает промпт для генерации контент-плана"""
        prompt = f"""Ты — профессиональный контент-стратег.
Тематика: {theme}
Стилистика: {style}

Создай контент-план на месяц (30 дней) для социальных сетей.
План должен включать:
1. Темы постов для каждого дня
2. Идеи для визуального контента
3. Рекомендации по времени публикации
4. Ключевые сообщения

Формат: простой список без лишних символов (*).
Пиши кратко и по делу.

Контент-план на месяц:"""

        return prompt