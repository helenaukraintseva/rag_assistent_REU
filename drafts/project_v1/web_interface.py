"""
Flask приложение для ИИ-консультанта.
Использует базу знаний в формате словаря и передает ИИ только ключи.
"""

from flask import Flask, render_template, request, jsonify
from retriever import get_retriever, KeyRetriever
from llm_client import llm_client
from knowledge_base import kb
import logging
from datetime import datetime
from typing import Dict, Any, List
import json

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация ретривера
try:
    retriever: KeyRetriever = get_retriever()
    health = retriever.health_check()
    logger.info(f"Ретривер инициализирован: {health}")
except Exception as e:
    logger.error(f"Ошибка инициализации ретривера: {e}")
    retriever = None


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/api/ask', methods=['POST'])
def ask_question():
    """
    Основной API эндпоинт.
    Этапы:
    1. Поиск релевантных ключей в базе знаний
    2. Передача ключей (НЕ СОДЕРЖИМОГО) в LLM
    3. Формирование ответа на основе ключей
    """
    if retriever is None:
        return jsonify({
            'success': False,
            'error': 'Ретривер не инициализирован',
            'answer': 'Система временно недоступна'
        }), 500

    try:
        # Получаем данные запроса
        data = request.get_json()
        if not data:
            data = request.form

        question = data.get('question', '').strip()
        top_k = int(data.get('top_k', 5))  # Количество ключей для поиска
        threshold = float(data.get('threshold', 0.1))  # Порог релевантности

        if not question:
            return jsonify({
                'success': False,
                'error': 'Пустой вопрос',
                'answer': 'Пожалуйста, задайте вопрос'
            })

        logger.info(f"Запрос: '{question}' (top_k={top_k}, threshold={threshold})")

        # ШАГ 1: Поиск релевантных ключей
        search_start = datetime.now()
        search_results = retriever.search(question, top_k=top_k, threshold=threshold)
        search_time = (datetime.now() - search_start).total_seconds()

        # Преобразуем результаты в словари для передачи
        key_results = [result.to_dict() for result in search_results]

        # ШАГ 2: Получение ответа от LLM (который видит только ключи)
        llm_start = datetime.now()

        if key_results:
            # Отправляем в LLM только ключи (не содержимое!)
            answer_data = llm_client.get_answer(question, key_results)
        else:
            # Если ключи не найдены
            answer_data = {
                "success": False,
                "answer": "По вашему вопросу не найдено релевантных документов.",
                "sources": [],
                "keys_used": []
            }

        llm_time = (datetime.now() - llm_start).total_seconds()

        # ШАГ 3: Формирование ответа
        response = {
            'success': True,
            'question': question,
            'answer': answer_data.get('answer', ''),
            'sources': answer_data.get('sources', []),
            'keys_used': answer_data.get('keys_used', []),
            'key_details': key_results,  # Детальная информация о ключах
            'keys_count': len(key_results),
            'search_time': round(search_time, 3),
            'llm_time': round(llm_time, 3),
            'total_time': round(search_time + llm_time, 3),
            'note': answer_data.get('note', '')
        }

        logger.info(f"Ответ готов. Ключей: {len(key_results)}, Время: {response['total_time']}с")

        return jsonify(response)

    except Exception as e:
        logger.error(f"Ошибка при обработке вопроса: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'answer': 'Произошла внутренняя ошибка сервера'
        }), 500


@app.route('/api/search_keys', methods=['POST'])
def search_keys_only():
    """
    Только поиск ключей без обращения к LLM.
    Полезно для отладки и для административного интерфейса.
    """
    if retriever is None:
        return jsonify({'success': False, 'error': 'Ретривер не инициализирован'}), 500

    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        top_k = int(data.get('top_k', 10))
        threshold = float(data.get('threshold', 0.0))

        if not query:
            return jsonify({'success': False, 'error': 'Пустой запрос'})

        start_time = datetime.now()
        results = retriever.search(query, top_k=top_k, threshold=threshold)
        search_time = (datetime.now() - start_time).total_seconds()

        return jsonify({
            'success': True,
            'query': query,
            'results': [r.to_dict() for r in results],
            'count': len(results),
            'search_time': round(search_time, 3)
        })

    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/key_content/<key>', methods=['GET'])
def get_key_content(key: str):
    """
    Получение полного содержимого документа по ключу.
    Только для административных целей, не используется в основном процессе.
    """
    try:
        content = kb.get_content_by_key(key)
        if content:
            return jsonify({
                'success': True,
                'key': key,
                'content': content
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Ключ "{key}" не найден'
            }), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/all_keys', methods=['GET'])
def get_all_keys():
    """Получение списка всех ключей в базе знаний"""
    try:
        keys = kb.get_all_keys()
        keys_info = []
        for key in keys:
            data = kb.knowledge_base[key]
            keys_info.append({
                'key': key,
                'title': data.get('title', key),
                'category': data.get('category', 'general')
            })

        return jsonify({
            'success': True,
            'keys': keys_info,
            'total': len(keys_info)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Проверка состояния системы"""
    if retriever is None:
        return jsonify({
            'status': 'error',
            'message': 'Ретривер не инициализирован'
        }), 500

    try:
        kb_health = retriever.health_check()

        # Проверяем доступность LLM API простым тестовым запросом
        llm_available = False
        try:
            test_keys = retriever.search("тест", top_k=1)
            if test_keys:
                test_response = llm_client.get_answer("тест", [test_keys[0].to_dict()])
                llm_available = test_response['success']
        except:
            pass

        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'knowledge_base': {
                'loaded': kb_health.get('loaded', False),
                'total_entries': kb_health.get('total_entries', 0),
                'index_size': kb_health.get('index_size', 0)
            },
            'llm_api': {
                'available': llm_available,
                'model': llm_client.model
            },
            'retriever': {
                'healthy': True
            }
        })

    except Exception as e:
        logger.error(f"Ошибка health check: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """Статистика системы"""
    if retriever is None:
        return jsonify({'error': 'Ретривер не инициализирован'}), 500

    try:
        stats = retriever.get_stats()

        # Добавляем информацию о категориях
        categories = {}
        for key, data in kb.knowledge_base.items():
            cat = data.get('category', 'general')
            categories[cat] = categories.get(cat, 0) + 1

        stats['categories'] = categories
        stats['total_entries'] = len(kb.get_all_keys())

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)