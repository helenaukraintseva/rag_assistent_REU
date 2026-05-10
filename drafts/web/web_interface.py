# app.py
from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for
import logging
from datetime import datetime, timedelta
import hashlib
import secrets
from functools import wraps
import os

# Импорты из наших модулей
from config import config
from models import db, User, UserSession, UserQuery, RetrievedDocument, QueryFeedback, KnowledgeBase, ActivityLog
from extensions import db, migrate, cache, cors, redis_client
from api_client import PolzaAIClient
from ai_program import AIKeySelector, AIGenerator
from data import KNOWLEDGE_BASE

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание приложения
app = Flask(__name__)
app.config.from_object(config['development'])  # Используем development конфигурацию

# Инициализация расширений
db.init_app(app)
migrate.init_app(app, db)
cache.init_app(app)
cors.init_app(app)

# Инициализация AI компонентов
key_selector = AIKeySelector()
answer_generator = AIGenerator()

# Данные для уроков и правил (можно потом перенести в БД)
LESSONS_DATA = [
    {
        'id': 1,
        'title': 'Введение в искусственный интеллект',
        'description': 'Основные концепции AI, история развития, современные подходы',
        'full_description': 'Подробное введение в мир искусственного интеллекта. Рассматриваются основные понятия, история развития от первых экспертных систем до современных нейросетей.',
        'topics': ['История AI', 'Машинное обучение', 'Нейронные сети', 'Deep Learning'],
        'duration': '2 часа',
        'materials': '5 лекций, 3 практики',
        'content': '''
            <h5>Модуль 1: История AI</h5>
            <p>От Тьюринга до современных трансформеров</p>
            <h5>Модуль 2: Машинное обучение</h5>
            <p>Supervised, Unsupervised, Reinforcement Learning</p>
        '''
    },
    {
        'id': 2,
        'title': 'Нейронные сети и глубокое обучение',
        'description': 'Архитектуры нейросетей, методы обучения, практическое применение',
        'topics': ['Перцептроны', 'CNN', 'RNN', 'Transformers'],
        'duration': '3 часа',
        'materials': '8 лекций, 5 практик'
    },
    {
        'id': 3,
        'title': 'Обработка естественного языка',
        'description': 'NLP, трансформеры, языковые модели',
        'topics': ['Токенизация', 'Embeddings', 'BERT', 'GPT'],
        'duration': '2.5 часа',
        'materials': '6 лекций, 4 практики'
    }
]

RULES_DATA = [
    {
        'id': 1,
        'category': 'Общие правила',
        'title': 'Правила поведения в университете',
        'content': '''
            <p><strong>1.1</strong> Студенты обязаны соблюдать дисциплину и уважать других учащихся</p>
            <p><strong>1.2</strong> Запрещается использование мобильных телефонов во время занятий</p>
            <p><strong>1.3</strong> Необходимо соблюдать чистоту в учебных аудиториях</p>
        ''',
        'additional': 'За нарушение правил предусмотрены взыскания вплоть до отчисления',
        'updated': '01.09.2024'
    },
    {
        'id': 2,
        'category': 'Академические правила',
        'title': 'Правила сдачи экзаменов',
        'content': '''
            <p><strong>2.1</strong> Экзамены проводятся в соответствии с расписанием сессии</p>
            <p><strong>2.2</strong> Для допуска к экзамену необходимо сдать все лабораторные работы</p>
            <p><strong>2.3</strong> Пересдачи проводятся не более 3 раз</p>
        ''',
        'additional': 'График пересдач утверждается деканатом',
        'updated': '01.09.2024'
    }
]


# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


# Создание таблиц БД при запуске
with app.app_context():
    db.create_all()

    # Инициализация базы знаний, если она пуста
    if KnowledgeBase.query.count() == 0:
        for key, content in KNOWLEDGE_BASE.items():
            kb_entry = KnowledgeBase(
                key=key,
                title=key.capitalize(),
                content=content.strip(),
                category='knowledge',
                tags=[key]
            )
            db.session.add(kb_entry)
        db.session.commit()
        logger.info("База знаний инициализирована")


# Маршруты
@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/ask')
@login_required
def ask():
    """Страница с AI помощником"""
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация пользователя"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')

        # Валидация
        if not all([username, email, password, confirm]):
            flash('Все поля обязательны для заполнения', 'error')
            return redirect(url_for('register'))

        if password != confirm:
            flash('Пароли не совпадают', 'error')
            return redirect(url_for('register'))

        # Проверка существования пользователя
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'error')
            return redirect(url_for('register'))

        # Создание пользователя
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            student_id=f"STU{secrets.randbelow(10000):04d}",
            created_at=datetime.utcnow()
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # Автоматический вход
        session['user_id'] = user.id
        session['username'] = user.username
        session.permanent = True

        flash('Регистрация прошла успешно!', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Вход пользователя"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'

        # Поиск пользователя
        user = User.query.filter(
            (User.email == username) | (User.username == username)
        ).first()

        if user and user.check_password(password) and user.is_active:
            # Обновление информации о входе
            user.last_login = datetime.utcnow()
            user.login_count += 1
            db.session.commit()

            # Создание сессии
            session['user_id'] = user.id
            session['username'] = user.username
            session.permanent = remember

            # Создание записи о сессии в БД
            user_session = UserSession(
                user_id=user.id,
                session_token=secrets.token_urlsafe(64),
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string[:500] if request.user_agent else None,
                login_time=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=7 if remember else 1)
            )
            db.session.add(user_session)
            db.session.commit()

            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('index'))

        flash('Неверное имя пользователя или пароль', 'error')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


@app.route('/lessons')
@login_required
def lessons():
    """Страница с уроками"""
    search_query = request.args.get('search', '').lower()

    if search_query:
        filtered_lessons = []
        for lesson in LESSONS_DATA:
            if (search_query in lesson['title'].lower() or
                    search_query in lesson['description'].lower() or
                    any(search_query in topic.lower() for topic in lesson.get('topics', []))):
                filtered_lessons.append(lesson)
    else:
        filtered_lessons = LESSONS_DATA

    return render_template('lessons.html', lessons=filtered_lessons, search_query=search_query)


@app.route('/rules')
@login_required
def rules():
    """Страница с правилами"""
    search_query = request.args.get('search', '').lower()

    if search_query:
        filtered_rules = []
        for rule in RULES_DATA:
            if (search_query in rule['title'].lower() or
                    search_query in rule['content'].lower() or
                    search_query in rule['category'].lower()):
                filtered_rules.append(rule)
    else:
        filtered_rules = RULES_DATA

    return render_template('rules.html', rules=filtered_rules, search_query=search_query)


@app.route('/api/ask', methods=['POST'])
@login_required
def ask_question():
    """API для вопросов к AI"""
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        use_ai_selection = data.get('use_ai_selection', True)

        if not question:
            return jsonify({'success': False, 'error': 'Пустой вопрос'})

        logger.info(f"Вопрос от пользователя {session['user_id']}: '{question}'")

        start_time = datetime.now()

        # Сохраняем запрос в БД
        user_query = UserQuery(
            user_id=session['user_id'],
            question=question,
            query_type='general',
            created_at=datetime.utcnow()
        )
        db.session.add(user_query)
        db.session.flush()

        # Выбор релевантного ключа
        if use_ai_selection:
            selection_result = key_selector.select_key(question, list(KNOWLEDGE_BASE.keys()))
        else:
            selection_result = key_selector._fallback_key_selection(question, list(KNOWLEDGE_BASE.keys()))

        selected_key = selection_result.get('selected_key')
        selection_time = (datetime.now() - start_time).total_seconds()

        # Генерация ответа
        if selected_key and selected_key in KNOWLEDGE_BASE:
            context = KNOWLEDGE_BASE[selected_key]

            # Сохраняем документ в БД
            kb_entry = KnowledgeBase.query.filter_by(key=selected_key).first()
            if kb_entry:
                retrieved = RetrievedDocument(
                    query_id=user_query.id,
                    document_id=str(kb_entry.id),
                    document_type=kb_entry.category,
                    title=kb_entry.title,
                    content=context[:500],
                    source='knowledge_base',
                    relevance_score=selection_result.get('confidence', 0.9),
                    rank=1
                )
                db.session.add(retrieved)
                kb_entry.queries_count += 1

            # Генерация ответа через AI
            generation_start = datetime.now()
            answer = answer_generator.generate_answer(question, context, selected_key)
            generation_time = (datetime.now() - generation_start).total_seconds()

            total_time = selection_time + generation_time

            # Обновляем запрос
            user_query.answer = answer
            user_query.selected_keys = [selected_key]
            user_query.used_llm = True
            user_query.confidence = selection_result.get('confidence', 0.9)
            user_query.response_time = total_time
            db.session.commit()

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
                'query_id': user_query.id
            }

        else:
            total_time = (datetime.now() - start_time).total_seconds()
            answer = "Извините, я не нашел информации по вашему вопросу в базе знаний."

            user_query.answer = answer
            user_query.confidence = 0
            user_query.response_time = total_time
            db.session.commit()

            response = {
                'success': True,
                'question': question,
                'answer': answer,
                'sources': [],
                'documents': [],
                'documents_count': 0,
                'search_time': selection_time,
                'llm_time': 0,
                'total_time': total_time,
                'used_llm': False,
                'query_id': user_query.id
            }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Ошибка при обработке вопроса: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/feedback', methods=['POST'])
@login_required
def submit_feedback():
    """API для обратной связи"""
    try:
        data = request.get_json()
        query_id = data.get('query_id')
        rating = data.get('rating')
        was_helpful = data.get('was_helpful')
        feedback_text = data.get('feedback_text')

        query = UserQuery.query.filter_by(id=query_id, user_id=session['user_id']).first()
        if not query:
            return jsonify({'success': False, 'error': 'Запрос не найден'})

        feedback = QueryFeedback(
            query_id=query_id,
            user_id=session['user_id'],
            rating=rating,
            was_helpful=was_helpful,
            feedback_text=feedback_text,
            created_at=datetime.utcnow()
        )
        db.session.add(feedback)
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Ошибка при сохранении отзыва: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/user/history')
@login_required
def user_history():
    """История запросов пользователя"""
    try:
        queries = UserQuery.query.filter_by(user_id=session['user_id']) \
            .order_by(UserQuery.created_at.desc()) \
            .limit(20).all()

        return jsonify({
            'success': True,
            'queries': [q.to_dict() for q in queries]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/health')
def health_check():
    """Проверка здоровья системы"""
    try:
        # Проверка БД
        db.session.execute('SELECT 1')

        # Проверка Polza.ai API
        test_response = key_selector.client.generate_content("test", max_tokens=5)

        return jsonify({
            'status': 'ok',
            'database': 'connected',
            'polza_api': bool(test_response),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/stats')
def get_stats():
    """Статистика системы"""
    try:
        total_users = User.query.count()
        total_queries = UserQuery.query.count()
        total_docs = KnowledgeBase.query.count()

        return jsonify({
            'success': True,
            'stats': {
                'total_users': total_users,
                'total_queries': total_queries,
                'total_documents': total_docs,
                'knowledge_base_keys': list(KNOWLEDGE_BASE.keys())
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)