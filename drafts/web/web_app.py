# app.py (обновленная версия)
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import logging
import secrets
from models import db, User, UserSession, KnowledgeBase, Lesson, Rule, UserQuery
from config import Config

from data import KNOWLEDGE_BASE
from ai_program import AIKeySelector, AIGenerator

app = Flask(__name__)
app.config.from_object(Config)

# Инициализация расширений
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

key_selector = AIKeySelector()
answer_generator = AIGenerator()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.before_request
def before_request():
    if current_user.is_authenticated:
        # Обновляем последнюю активность
        session = UserSession.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).order_by(UserSession.last_activity.desc()).first()
        if session:
            session.last_activity = datetime.utcnow()
            db.session.commit()


@app.route('/')
def index():
    """Главная страница с AI-ассистентом"""
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация пользователя"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        role = request.form.get('role')

        # Проверка паролей
        if password != confirm_password:
            flash('Пароли не совпадают', 'danger')
            return redirect(url_for('register'))

        # Проверка существующего пользователя
        if User.query.filter_by(username=username).first():
            flash('Логин уже занят', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email уже зарегистрирован', 'danger')
            return redirect(url_for('register'))

        # Создание пользователя
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role
        )

        if role == 'student':
            user.faculty = request.form.get('faculty')
            user.group = request.form.get('group')
        else:
            user.position = request.form.get('position')

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # Создание сессии
        session_token = secrets.token_urlsafe(32)
        user_session = UserSession(
            user_id=user.id,
            session_token=session_token,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        db.session.add(user_session)
        db.session.commit()

        login_user(user)
        flash('Регистрация успешна!', 'success')
        return redirect(url_for('index'))

    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Вход в систему"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Аккаунт деактивирован', 'danger')
                return redirect(url_for('login'))

            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()

            # Создание сессии
            session_token = secrets.token_urlsafe(32)
            user_session = UserSession(
                user_id=user.id,
                session_token=session_token,
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            db.session.add(user_session)
            db.session.commit()

            flash('Вход выполнен успешно', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверный email или пароль', 'danger')

    return render_template('auth/login.html')


@app.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    # Закрываем активные сессии
    UserSession.query.filter_by(user_id=current_user.id, is_active=True).update({
        'is_active': False,
        'logout_time': datetime.utcnow()
    })
    db.session.commit()

    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


@app.route('/lessons')
def lessons():
    """Страница уроков"""
    page = request.args.get('page', 1, type=int)
    faculty = request.args.get('faculty', '')
    lesson_type = request.args.get('type', '')
    day = request.args.get('day', '', type=int)

    query = Lesson.query

    if faculty:
        query = query.filter_by(faculty=faculty)
    if lesson_type:
        query = query.filter_by(lesson_type=lesson_type)
    if day is not None:
        query = query.filter_by(weekday=day)

    pagination = query.paginate(page=page, per_page=12, error_out=False)
    lessons = pagination.items

    return render_template('lessons.html',
                           lessons=lessons,
                           pagination=pagination,
                           current_page=page,
                           total_pages=pagination.pages)


@app.route('/lesson/<int:lesson_id>')
def lesson_detail(lesson_id):
    """Детальная страница урока"""
    lesson = Lesson.query.get_or_404(lesson_id)
    return render_template('lesson_detail.html', lesson=lesson)


@app.route('/rules')
def rules():
    """Страница правил"""
    category = request.args.get('category', 'all')

    query = Rule.query.filter_by(is_active=True)
    if category != 'all':
        query = query.filter_by(category=category)

    rules = query.order_by(Rule.order_index).all()
    return render_template('rules.html', rules=rules, now=datetime.now)


@app.route('/profile')
@login_required
def profile():
    """Профиль пользователя"""
    return render_template('profile.html', user=current_user)


@app.route('/my-queries')
@login_required
def my_queries():
    """История запросов пользователя"""
    page = request.args.get('page', 1, type=int)
    queries = UserQuery.query.filter_by(user_id=current_user.id) \
        .order_by(UserQuery.created_at.desc()) \
        .paginate(page=page, per_page=10)
    return render_template('queries.html', queries=queries)


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
                'selection_method': selection_result.get('method', 'ai')
            }

            logger.info(f"Ответ готов. Ключ: {selected_key}, Время: {total_time:.2f}с")

        else:
            # Ключ не найден
            total_time = (datetime.now() - start_time).total_seconds()

            response = {
                'success': True,
                'question': question,
                'answer': "Извините, я не нашел информации по вашему вопросу в базе знаний. Пожалуйста, уточните вопрос или обратитесь в деканат.",
                'sources': [],
                'documents': [],
                'documents_count': 0,
                'search_time': selection_time,
                'llm_time': 0,
                'total_time': total_time,
                'used_llm': True,
                'llm_success': True
            }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Ошибка при обработке вопроса: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'answer': '',
            'documents': []
        })


@app.route('/api/feedback', methods=['POST'])
@login_required
def submit_feedback():
    """Оценка ответа AI"""
    data = request.get_json()
    query_id = data.get('query_id')
    score = data.get('score')
    feedback = data.get('feedback')

    query = UserQuery.query.get_or_404(query_id)
    if query.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    query.feedback_score = score
    query.feedback_text = feedback
    db.session.commit()

    return jsonify({'success': True})


@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    """Панель преподавателя"""
    if not current_user.is_teacher():
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    # Статистика
    total_lessons = Lesson.query.filter_by(teacher_id=current_user.id).count()
    today_lessons = Lesson.query.filter_by(
        teacher_id=current_user.id,
        weekday=datetime.now().weekday()
    ).count()

    return render_template('teacher/dashboard.html',
                           total_lessons=total_lessons,
                           today_lessons=today_lessons)


# Инициализация базы данных
@app.cli.command("init-db")
def init_db():
    """Инициализация базы данных"""
    db.create_all()

    # Добавление тестовых правил
    rules = [
        Rule(title="Общие правила поведения",
             content="1. Соблюдать учебную дисциплину\n2. Уважать преподавателей\n3. Беречь имущество",
             category="general", order_index=1),
        Rule(title="Правила посещаемости",
             content="Посещаемость не менее 70% занятий для допуска к сессии",
             category="academic", order_index=2),
    ]

    for rule in rules:
        db.session.add(rule)

    # Добавление тестовых уроков
    from datetime import time
    lessons = [
        Lesson(title="Математический анализ",
               subject="Математика",
               lesson_type="lecture",
               weekday=0,
               start_time=time(9, 0),
               end_time=time(10, 30),
               classroom="301",
               building="Главный корпус"),
        Lesson(title="Программирование",
               subject="Информатика",
               lesson_type="practice",
               weekday=1,
               start_time=time(11, 0),
               end_time=time(12, 30),
               classroom="405",
               building="Главный корпус"),
    ]

    for lesson in lessons:
        db.session.add(lesson)

    db.session.commit()
    print("База данных инициализирована")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)