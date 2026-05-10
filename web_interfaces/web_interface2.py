# app.py
from flask import Flask, render_template, request, jsonify
from retriever import get_retriever
import logging
from datetime import datetime

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация ретривера (один раз при запуске)
try:
    retriever = get_retriever()
    logger.info("Ретривер успешно инициализирован")

    # Проверка работоспособности
    health = retriever.health_check()
    logger.info(f"Статус ретривера: {health}")

except Exception as e:
    logger.error(f"Ошибка инициализации ретривера: {e}")
    retriever = None


@app.route('/')
def index():
    """Главная страница с формой поиска"""
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    """Обработка поискового запроса"""
    if retriever is None:
        return jsonify({
            'success': False,
            'error': 'Ретривер не инициализирован',
            'results': []
        })

    try:
        # Получаем данные из формы
        data = request.get_json()
        if not data:
            data = request.form

        query = data.get('query', '').strip()
        k = int(data.get('k', 5))
        threshold = float(data.get('threshold', 0.0))

        if not query:
            return jsonify({
                'success': False,
                'error': 'Пустой запрос',
                'results': []
            })

        logger.info(f"Поиск запроса: '{query}' (k={k}, threshold={threshold})")

        # Выполняем поиск
        start_time = datetime.now()
        results = retriever.search(query, k=k, threshold=threshold)
        search_time = (datetime.now() - start_time).total_seconds()

        # Преобразуем результаты в словари
        formatted_results = []
        for result in results:
            formatted_results.append({
                'text': result.text,
                'source': result.source,
                'score': float(result.score),
                'metadata': result.metadata,
                'preview': result.text[:200] + ('...' if len(result.text) > 200 else '')
            })

        # Получаем статистику
        stats = retriever.get_index_stats()

        response = {
            'success': True,
            'query': query,
            'results': formatted_results,
            'count': len(results),
            'search_time': search_time,
            'stats': {
                'total_vectors': stats.get('total_vectors', 0),
                'metadata_count': stats.get('metadata_count', 0),
                'search_count': stats.get('search_count', 0)
            }
        }

        logger.info(f"Найдено результатов: {len(results)} за {search_time:.3f} сек")

        return jsonify(response)

    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'results': []
        })


@app.route('/health')
def health_check():
    """Проверка состояния системы"""
    if retriever is None:
        return jsonify({
            'status': 'error',
            'message': 'Ретривер не инициализирован'
        })

    try:
        health = retriever.health_check()
        stats = retriever.get_index_stats()

        return jsonify({
            'status': 'ok',
            'health': health,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })


@app.route('/stats')
def get_stats():
    """Получение статистики индекса"""
    if retriever is None:
        return jsonify({'error': 'Ретривер не инициализирован'})

    stats = retriever.get_index_stats()
    return jsonify(stats)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)