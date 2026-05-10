# web_interface.py
from flask import Flask, render_template, request, jsonify
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
from giga_chat_client import GigaChatClient

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импорт конфигурации с ключом
try:
    from config import MY_AUTH_KEY, SCOPE
except ImportError:
    logger.warning("config.py не найден. Используйте переменную окружения GIGACHAT_AUTH_KEY")
    import os

    MY_AUTH_KEY = os.getenv('GIGACHAT_AUTH_KEY', '')
    SCOPE = os.getenv('GIGACHAT_SCOPE', 'GIGACHAT_API_PERS')

# База знаний (ключи и их содержимое)
KNOWLEDGE_BASE = {
    "расписание занятий": """
        Расписание занятий на текущий семестр:
        - Понедельник: 9:00-10:30 Лекция по математике (ауд. 301)
        - Вторник: 11:00-12:30 Практикум по программированию (ауд. 405)
        - Среда: 14:00-15:30 Семинар по физике (ауд. 202)
        - Четверг: 10:00-11:30 Лабораторная по химии (ауд. 115)
        - Пятница: 13:00-14:30 Английский язык (ауд. 308)

        Расписание может меняться, следите за объявлениями на доске в холле.
    """,

    "правила обучения": """
        Правила обучения в университете:
        1. Посещаемость: обязательно посещение не менее 70% занятий
        2. Оценки: шкала от 2 до 5, зачеты - зачтено/не зачтено
        3. Сессия: два раза в год (зимняя и летняя)
        4. Пересдачи: допускается до 3 пересдач по каждому предмету
        5. Академический отпуск: можно взять по состоянию здоровья или семейным обстоятельствам
        6. Стипендия: назначается при оценках 4 и 5
        7. Отчисление: при трех и более несданных экзаменах или грубых нарушениях дисциплины
    """,

    "контакты деканата": """
        Контакты деканата:
        - Декан: Иванов Иван Иванович, каб. 210, тел. 8 (123) 456-78-90
        - Зам. декана: Петрова Анна Сергеевна, каб. 211, тел. 8 (123) 456-78-91
        - Секретарь: Сидорова Мария Петровна, каб. 209, тел. 8 (123) 456-78-92
        - Методист: Кузнецов Алексей Владимирович, каб. 208, тел. 8 (123) 456-78-93

        Часы приема: 
        - Пн-Пт: 10:00 - 17:00
        - Перерыв: 13:00 - 14:00
        - Сб-Вс: выходной

        Email: dean@university.ru
    """,

    "библиотека": """
        Информация о библиотеке:
        - Режим работы: Пн-Пт 9:00-20:00, Сб 10:00-17:00, Вс - выходной
        - Абонемент: выдача книг на дом (до 30 дней)
        - Читальный зал: 120 мест, доступ к электронным ресурсам
        - Электронный каталог: library.university.ru
        - Межбиблиотечный абонемент: заказ книг из других библиотек
        - Услуги: сканирование, печать, ксерокопирование
        - Контакты: library@university.ru, тел. 8 (123) 456-78-94
    """,

    "студенческий совет": """
        Студенческий совет:
        - Председатель: Соколов Дмитрий, тел. 8 (999) 123-45-67
        - Культмассовый сектор: организация мероприятий
        - Спортивный сектор: секции и соревнования
        - Волонтерский центр: помощь и акции
        - Медиацентр: газета "Студенческий вестник" и соцсети

        Заседания: каждый вторник в 18:00, актовый зал
        Вступайте в группу ВК: vk.com/student_soviet
    """,

    "стипендия": """
        Информация о стипендиях:
        - Академическая: от 2000 руб. (при оценках 4 и 5)
        - Повышенная: от 5000 руб. (за особые достижения)
        - Социальная: для льготных категорий
        - Именные: от компаний-партнеров

        Условия получения:
        - Отсутствие задолженностей
        - Средний балл не ниже 4.0
        - Участие в научной/общественной жизни

        Оформление: деканат, каб. 209, до 25 числа каждого месяца
    """,

    "общежитие": """
        Информация об общежитии:
        - Адрес: ул. Студенческая, д. 15
        - Типы комнат: 2-3 местные, блоки на 2 комнаты
        - Стоимость: 800 руб./месяц
        - Заселение: при наличии мест, по заявлению в деканат

        Удобства:
        - Кухни на этаже
        - Душевые на этаже
        - Стиральные машины (платно)
        - Wi-Fi на всей территории
        - Спортзал в цокольном этаже

        Комендант: Васильева Елена Петровна, ком. 101, тел. 8 (123) 456-78-95
    """
}


class GigaChatKeySelector:
    """Класс для выбора ключа с помощью GigaChat"""

    def __init__(self, auth_key: str, scope: str = "GIGACHAT_API_PERS"):
        self.client = GigaChatClient(auth_key=auth_key, scope=scope)
        logger.info("GigaChat Key Selector инициализирован")

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
            response = self.client.process_prompt(prompt, max_tokens=50)

            # Очищаем ответ от лишних пробелов и символов
            if response:
                response = response.strip().lower()

                # Проверяем, совпадает ли с одним из ключей
                for key in available_keys:
                    if key.lower() == response or response in key.lower() or key.lower() in response:
                        selected_key = key
                        logger.info(f"Выбран ключ: {selected_key}")
                        return {
                            "success": True,
                            "selected_key": selected_key,
                            "confidence": 1.0
                        }

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


class GigaChatAnswerGenerator:
    """Класс для генерации ответа с помощью GigaChat"""

    def __init__(self, auth_key: str, scope: str = "GIGACHAT_API_PERS"):
        self.client = GigaChatClient(auth_key=auth_key, scope=scope)
        logger.info("GigaChat Answer Generator инициализирован")

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

Не используй звездочки (*) и другие специальные символы для форматирования.
Пиши простым и понятным языком.

Ответ:"""

        try:
            response = self.client.process_prompt(
                prompt,
                max_tokens=1000,
                temperature=0.7
            )
            return response if response else "Извините, не удалось сгенерировать ответ."
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            return "Произошла ошибка при генерации ответа. Пожалуйста, попробуйте позже."


# Проверка наличия ключа
if not MY_AUTH_KEY:
    logger.error("AUTH_KEY не найден! Укажите ключ в config.py или переменной окружения GIGACHAT_AUTH_KEY")
    print("\n" + "=" * 50)
    print("ОШИБКА: Не указан ключ авторизации GigaChat!")
    print("Создайте файл config.py с переменной MY_AUTH_KEY")
    print("Или установите переменную окружения GIGACHAT_AUTH_KEY")
    print("=" * 50 + "\n")

# Инициализация компонентов с GigaChat
key_selector = GigaChatKeySelector(auth_key=MY_AUTH_KEY, scope=SCOPE)
answer_generator = GigaChatAnswerGenerator(auth_key=MY_AUTH_KEY, scope=SCOPE)


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/api/ask', methods=['POST'])
def ask_question():
    """Основной API эндпоинт для вопросов"""
    try:
        data = request.get_json()
        if not data:
            data = request.form

        question = data.get('question', '').strip()
        use_ai_selection = data.get('use_ai_selection', True)

        if not question:
            return jsonify({
                'success': False,
                'error': 'Пустой вопрос',
                'answer': '',
                'documents': []
            })

        logger.info(f"Вопрос: '{question}' (AI selection: {use_ai_selection})")

        start_time = datetime.now()

        # Шаг 1: Выбор релевантного ключа
        if use_ai_selection:
            selection_result = key_selector.select_key(question, list(KNOWLEDGE_BASE.keys()))
        else:
            # Используем fallback метод
            selection_result = key_selector._fallback_key_selection(question, list(KNOWLEDGE_BASE.keys()))

        selected_key = selection_result.get('selected_key')
        selection_time = (datetime.now() - start_time).total_seconds()

        # Шаг 2: Если ключ выбран, получаем контекст и генерируем ответ
        if selected_key and selected_key in KNOWLEDGE_BASE:
            context = KNOWLEDGE_BASE[selected_key]

            # Генерируем ответ
            generation_start = datetime.now()
            answer = answer_generator.generate_answer(question, context, selected_key)
            generation_time = (datetime.now() - generation_start).total_seconds()

            total_time = selection_time + generation_time

            # Формируем документы для отображения в интерфейсе
            documents = [{
                'text': context,
                'source': selected_key,
                'score': selection_result.get('confidence', 1.0),
                'metadata': {'key': selected_key},
                'preview': context[:200] + '...'
            }]

            response = {
                'success': True,
                'question': question,
                'answer': answer,
                'sources': [selected_key],
                'documents': documents,
                'documents_count': 1,
                'search_time': selection_time,
                'llm_time': generation_time,
                'total_time': total_time,
                'used_llm': True,
                'llm_success': True,
                'selection_method': selection_result.get('method', 'ai'),
                'llm_provider': 'GigaChat'
            }

            logger.info(f"Ответ готов. Ключ: {selected_key}, Время: {total_time:.2f}с")

        else:
            # Ключ не найден
            total_time = (datetime.now() - start_time).total_seconds()

            # Пытаемся сгенерировать общий ответ
            fallback_answer = answer_generator.generate_answer(
                question,
                "Информация не найдена в базе знаний.",
                "общее"
            )

            response = {
                'success': True,
                'question': question,
                'answer': fallback_answer or "Извините, я не нашел информации по вашему вопросу в базе знаний. Пожалуйста, уточните вопрос или обратитесь в деканат.",
                'sources': [],
                'documents': [],
                'documents_count': 0,
                'search_time': selection_time,
                'llm_time': 0,
                'total_time': total_time,
                'used_llm': True,
                'llm_success': True,
                'llm_provider': 'GigaChat'
            }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Ошибка при обработке вопроса: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'answer': 'Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.',
            'documents': []
        })


@app.route('/api/available_keys', methods=['GET'])
def get_available_keys():
    """Возвращает список доступных ключей"""
    return jsonify({
        'success': True,
        'keys': list(KNOWLEDGE_BASE.keys())
    })


@app.route('/api/test_llm', methods=['POST'])
def test_llm():
    """Тестирование соединения с GigaChat API"""
    try:
        test_prompt = "Тестовый запрос: ответь 'OK' если соединение работает."
        response = key_selector.client.process_prompt(test_prompt, max_tokens=10)

        return jsonify({
            'success': response is not None and len(response) > 0,
            'message': 'GigaChat API доступен' if response else 'GigaChat API недоступен',
            'details': {'response': response},
            'provider': 'GigaChat'
        })
    except Exception as e:
        logger.error(f"Ошибка тестирования GigaChat: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Ошибка соединения с GigaChat API',
            'provider': 'GigaChat'
        })


@app.route('/health')
def health_check():
    """Проверка состояния системы"""
    try:
        # Проверяем API ключей
        has_auth_key = bool(MY_AUTH_KEY)

        return jsonify({
            'status': 'ok',
            'knowledge_base': {
                'keys_count': len(KNOWLEDGE_BASE),
                'keys': list(KNOWLEDGE_BASE.keys())
            },
            'llm_api': {
                'available': has_auth_key,
                'type': 'GigaChat',
                'configured': has_auth_key
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })


@app.route('/stats')
def get_stats():
    """Статистика системы"""
    return jsonify({
        'total_keys': len(KNOWLEDGE_BASE),
        'keys': list(KNOWLEDGE_BASE.keys()),
        'total_characters': sum(len(text) for text in KNOWLEDGE_BASE.values()),
        'llm_provider': 'GigaChat',
        'auth_configured': bool(MY_AUTH_KEY)
    })


if __name__ == '__main__':
    if not MY_AUTH_KEY:
        print("\n" + "=" * 60)
        print("⚠️  ВНИМАНИЕ: Не указан ключ авторизации GigaChat!")
        print("Создайте файл config.py со следующим содержимым:")
        print("MY_AUTH_KEY = 'ваш_ключ_авторизации'")
        print("SCOPE = 'GIGACHAT_API_PERS'")
        print("=" * 60 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)