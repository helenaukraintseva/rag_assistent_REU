# web_interface.py
from flask import Flask, render_template, request, jsonify
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import os
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

# Путь к JSON файлу с базой знаний
KNOWLEDGE_BASE_FILE = os.getenv('KNOWLEDGE_BASE_FILE', 'qa_format_with_links.json')

# Глобальная переменная для хранения базы знаний
KNOWLEDGE_BASE = {}


def load_knowledge_base(file_path: str) -> Dict[str, Any]:
    """
    Загружает базу знаний из JSON файла

    Args:
        file_path: путь к JSON файлу

    Returns:
        словарь с базой знаний
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"Файл {file_path} не найден!")
            return {}

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Преобразуем структуру JSON в формат KNOWLEDGE_BASE
        knowledge_base = {}

        for key, value in data.items():
            # Извлекаем текст документа
            text = value.get('text', '')
            doc_link = value.get('doc_link', '')

            # Сохраняем в базу знаний
            knowledge_base[key] = {
                'text': text,
                'doc_link': doc_link
            }

        logger.info(f"Загружено {len(knowledge_base)} документов из {file_path}")
        return knowledge_base

    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON файла: {e}")
        return {}
    except Exception as e:
        logger.error(f"Ошибка загрузки базы знаний: {e}")
        return {}


def reload_knowledge_base():
    """Перезагружает базу знаний из JSON файла"""
    global KNOWLEDGE_BASE
    KNOWLEDGE_BASE = load_knowledge_base(KNOWLEDGE_BASE_FILE)
    logger.info(f"База знаний перезагружена. Доступно {len(KNOWLEDGE_BASE)} документов")


# Загружаем базу знаний при старте
reload_knowledge_base()


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
                            "confidence": 1.0,
                            "doc_link": KNOWLEDGE_BASE.get(selected_key, {}).get('doc_link', '')
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
                "method": "fallback",
                "doc_link": KNOWLEDGE_BASE.get(best_key, {}).get('doc_link', '')
            }

        return {
            "success": False,
            "selected_key": None,
            "confidence": 0,
            "message": "Не удалось определить релевантный раздел",
            "doc_link": ""
        }


class GigaChatAnswerGenerator:
    """Класс для генерации ответа с помощью GigaChat"""

    def __init__(self, auth_key: str, scope: str = "GIGACHAT_API_PERS"):
        self.client = GigaChatClient(auth_key=auth_key, scope=scope)
        logger.info("GigaChat Answer Generator инициализирован")

    def generate_answer(self, question: str, context: str, key: str, doc_link: str = "") -> str:
        """Генерирует ответ на основе контекста"""

        # Добавляем информацию о ссылке на документ, если она есть
        # doc_link_text = f"\n\nСсылка на источник: {doc_link}" if doc_link else ""

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

Если в ответе нужно указать ссылку на источник - включи её в ответ.

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

# Проверка загрузки базы знаний
if not KNOWLEDGE_BASE:
    logger.warning("База знаний не загружена или пуста!")
    print("\n" + "=" * 50)
    print("ПРЕДУПРЕЖДЕНИЕ: База знаний не загружена!")
    print(f"Проверьте наличие файла: {KNOWLEDGE_BASE_FILE}")
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
        available_keys = list(KNOWLEDGE_BASE.keys())

        if not available_keys:
            return jsonify({
                'success': False,
                'error': 'База знаний не загружена',
                'answer': 'Извините, база знаний временно недоступна. Пожалуйста, попробуйте позже.',
                'documents': []
            })

        if use_ai_selection:
            selection_result = key_selector.select_key(question, available_keys)
        else:
            # Используем fallback метод
            selection_result = key_selector._fallback_key_selection(question, available_keys)

        selected_key = selection_result.get('selected_key')
        selection_time = (datetime.now() - start_time).total_seconds()

        # Получаем ссылку на документ
        doc_link = selection_result.get('doc_link', '')

        # Шаг 2: Если ключ выбран, получаем контекст и генерируем ответ
        if selected_key and selected_key in KNOWLEDGE_BASE:
            context_data = KNOWLEDGE_BASE[selected_key]
            context = context_data.get('text', '')
            doc_link = doc_link or context_data.get('doc_link', '')

            # Генерируем ответ
            generation_start = datetime.now()
            answer = answer_generator.generate_answer(question, context, selected_key, doc_link)
            generation_time = (datetime.now() - generation_start).total_seconds()

            total_time = selection_time + generation_time

            # Формируем документы для отображения в интерфейсе
            documents = [{
                'text': context,
                'source': selected_key,
                'score': selection_result.get('confidence', 1.0),
                'metadata': {
                    'key': selected_key,
                    'doc_link': doc_link
                },
                'preview': context[:200] + '...' if len(context) > 200 else context,
                'doc_link': doc_link
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
                'llm_provider': 'GigaChat',
                'doc_link': doc_link
            }

            logger.info(f"Ответ готов. Ключ: {selected_key}, Время: {total_time:.2f}с")

        else:
            # Ключ не найден
            total_time = (datetime.now() - start_time).total_seconds()

            # Пытаемся сгенерировать общий ответ
            fallback_answer = answer_generator.generate_answer(
                question,
                "Информация не найдена в базе знаний.",
                "общее",
                ""
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
    keys_info = []
    for key, value in KNOWLEDGE_BASE.items():
        keys_info.append({
            'name': key,
            'doc_link': value.get('doc_link', ''),
            'text_preview': value.get('text', '')[:100] + '...' if len(value.get('text', '')) > 100 else value.get(
                'text', '')
        })

    return jsonify({
        'success': True,
        'keys': list(KNOWLEDGE_BASE.keys()),
        'keys_info': keys_info,
        'total_documents': len(KNOWLEDGE_BASE)
    })


@app.route('/api/reload_kb', methods=['POST'])
def reload_knowledge_base_api():
    """Перезагружает базу знаний из JSON файла"""
    try:
        reload_knowledge_base()
        return jsonify({
            'success': True,
            'message': f'База знаний перезагружена. Загружено {len(KNOWLEDGE_BASE)} документов.',
            'documents_count': len(KNOWLEDGE_BASE)
        })
    except Exception as e:
        logger.error(f"Ошибка перезагрузки базы знаний: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Ошибка при перезагрузке базы знаний'
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

        # Проверяем загрузку базы знаний
        kb_loaded = len(KNOWLEDGE_BASE) > 0

        return jsonify({
            'status': 'ok' if has_auth_key and kb_loaded else 'degraded',
            'knowledge_base': {
                'keys_count': len(KNOWLEDGE_BASE),
                'keys': list(KNOWLEDGE_BASE.keys())[:10],  # Показываем только первые 10 ключей
                'loaded': kb_loaded,
                'file_path': KNOWLEDGE_BASE_FILE
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
    total_length = sum(len(value.get('text', '')) for value in KNOWLEDGE_BASE.values())

    # Подсчет документов со ссылками
    docs_with_links = sum(1 for value in KNOWLEDGE_BASE.values() if value.get('doc_link'))

    return jsonify({
        'total_keys': len(KNOWLEDGE_BASE),
        'keys': list(KNOWLEDGE_BASE.keys()),
        'total_characters': total_length,
        'average_document_size': total_length // len(KNOWLEDGE_BASE) if KNOWLEDGE_BASE else 0,
        'documents_with_links': docs_with_links,
        'llm_provider': 'GigaChat',
        'auth_configured': bool(MY_AUTH_KEY),
        'kb_file': KNOWLEDGE_BASE_FILE
    })


@app.route('/api/search', methods=['POST'])
def search_in_knowledge_base():
    """Поиск по базе знаний"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip().lower()

        if not query:
            return jsonify({
                'success': False,
                'error': 'Пустой поисковый запрос'
            })

        results = []
        for key, value in KNOWLEDGE_BASE.items():
            text_lower = value.get('text', '').lower()
            if query in text_lower or query in key.lower():
                # Находим контекст вокруг искомого слова
                text = value.get('text', '')
                index = text_lower.find(query)
                start = max(0, index - 100)
                end = min(len(text), index + 200)
                context = text[start:end] + '...' if end < len(text) else text[start:end]

                results.append({
                    'key': key,
                    'doc_link': value.get('doc_link', ''),
                    'context': context,
                    'relevance': 'high' if query in key.lower() else 'medium'
                })

        return jsonify({
            'success': True,
            'query': query,
            'results': results,
            'results_count': len(results)
        })

    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })


if __name__ == '__main__':
    if not MY_AUTH_KEY:
        print("\n" + "=" * 60)
        print("⚠️  ВНИМАНИЕ: Не указан ключ авторизации GigaChat!")
        print("Создайте файл config.py со следующим содержимым:")
        print("MY_AUTH_KEY = 'ваш_ключ_авторизации'")
        print("SCOPE = 'GIGACHAT_API_PERS'")
        print("=" * 60 + "\n")

    if not KNOWLEDGE_BASE:
        print("\n" + "=" * 60)
        print("⚠️  ВНИМАНИЕ: База знаний не загружена!")
        print(f"Убедитесь, что файл {KNOWLEDGE_BASE_FILE} существует и содержит корректные данные.")
        print("=" * 60 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)