# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Index, text

db = SQLAlchemy()


class User(db.Model):
    """Модель пользователя (студента)"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    # Личная информация
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    middle_name = db.Column(db.String(50))
    birth_date = db.Column(db.Date)
    phone = db.Column(db.String(20))
    avatar_url = db.Column(db.String(500))

    # Учебная информация
    student_id = db.Column(db.String(20), unique=True)  # Номер студенческого билета
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'))
    course = db.Column(db.Integer)  # Курс (1-4)
    faculty = db.Column(db.String(100))  # Факультет
    specialization = db.Column(db.String(200))  # Специализация
    enrollment_year = db.Column(db.Integer)  # Год поступления
    graduation_year = db.Column(db.Integer)  # Год окончания

    # Статусы
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(20), default='student')  # student, teacher, admin

    # Системная информация
    last_login = db.Column(db.DateTime)
    last_active = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Настройки и предпочтения
    preferences = db.Column(JSONB, default={})
    notification_settings = db.Column(JSONB, default={})

    # Связи
    sessions = db.relationship('UserSession', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    queries = db.relationship('UserQuery', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    feedback = db.relationship('QueryFeedback', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    activity_logs = db.relationship('ActivityLog', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    # Индексы
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_student_id', 'student_id'),
        Index('idx_user_group', 'group_id'),
        Index('idx_user_course', 'course'),
    )

    def set_password(self, password):
        """Установка пароля"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Проверка пароля"""
        return check_password_hash(self.password_hash, password)

    def update_last_login(self):
        """Обновление времени последнего входа"""
        self.last_login = datetime.utcnow()
        self.login_count += 1

    def to_dict(self, include_sensitive=False):
        """Сериализация в словарь"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'middle_name': self.middle_name,
            'full_name': self.get_full_name(),
            'student_id': self.student_id,
            'group': self.group.name if self.group else None,
            'course': self.course,
            'faculty': self.faculty,
            'specialization': self.specialization,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }

        if include_sensitive:
            data.update({
                'phone': self.phone,
                'birth_date': self.birth_date.isoformat() if self.birth_date else None,
                'preferences': self.preferences,
                'notification_settings': self.notification_settings,
            })

        return data

    def get_full_name(self):
        """Получение полного имени"""
        parts = [self.last_name or '', self.first_name or '', self.middle_name or '']
        return ' '.join(filter(None, parts)).strip() or self.username

    def __repr__(self):
        return f'<User {self.username}>'


class Group(db.Model):
    """Модель учебной группы"""
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # Например: ИТ-201
    faculty = db.Column(db.String(100))
    course = db.Column(db.Integer)
    department = db.Column(db.String(100))  # Кафедра

    # Староста группы
    headman_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Учебный план
    curriculum = db.Column(JSONB, default={})  # JSON с расписанием и планом

    # Связи
    students = db.relationship('User', backref='group', lazy='dynamic', foreign_keys='User.group_id')
    headman = db.relationship('User', foreign_keys=[headman_id])

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'faculty': self.faculty,
            'course': self.course,
            'department': self.department,
            'headman': self.headman.get_full_name() if self.headman else None,
            'students_count': self.students.count()
        }


class UserSession(db.Model):
    """Модель сессии пользователя"""
    __tablename__ = 'user_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_token = db.Column(db.String(256), unique=True, nullable=False)

    # Информация о сессии
    ip_address = db.Column(db.String(45))  # IPv6 support
    user_agent = db.Column(db.String(500))
    device_type = db.Column(db.String(50))  # mobile, tablet, desktop
    browser = db.Column(db.String(50))
    os = db.Column(db.String(50))

    # Геолокация (если доступно)
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    # Временные метки
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    logout_time = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)

    is_active = db.Column(db.Boolean, default=True)

    # Индексы
    __table_args__ = (
        Index('idx_session_token', 'session_token'),
        Index('idx_session_user_active', 'user_id', 'is_active'),
    )

    def update_activity(self):
        """Обновление времени активности"""
        self.last_activity = datetime.utcnow()

    def end_session(self):
        """Завершение сессии"""
        self.logout_time = datetime.utcnow()
        self.is_active = False

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'device_type': self.device_type,
            'browser': self.browser,
            'os': self.os,
            'login_time': self.login_time.isoformat() if self.login_time else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'is_active': self.is_active,
            'location': f"{self.city}, {self.country}" if self.city and self.country else None
        }


class UserQuery(db.Model):
    """Модель запроса пользователя к AI"""
    __tablename__ = 'user_queries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('user_sessions.id'))

    # Запрос и ответ
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text)

    # Метаданные запроса
    query_type = db.Column(db.String(50))  # general, lessons, rules, etc.
    intent = db.Column(db.String(100))  # Распознанное намерение
    confidence = db.Column(db.Float)  # Уверенность в ответе

    # Выбранные ключи/разделы
    selected_keys = db.Column(JSONB, default=[])  # Какие разделы использованы
    used_llm = db.Column(db.Boolean, default=True)

    # Временные метки
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    response_time = db.Column(db.Float)  # Время ответа в секундах

    # Связи
    feedback = db.relationship('QueryFeedback', backref='query', uselist=False, cascade='all, delete-orphan')
    retrieved_documents = db.relationship('RetrievedDocument', backref='query', lazy='dynamic',
                                          cascade='all, delete-orphan')

    # Индексы
    __table_args__ = (
        Index('idx_query_user', 'user_id'),
        Index('idx_query_created', 'created_at'),
        Index('idx_query_type', 'query_type'),
    )

    def to_dict(self, include_documents=False):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'question': self.question,
            'answer': self.answer,
            'query_type': self.query_type,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'response_time': self.response_time,
            'used_llm': self.used_llm,
            'has_feedback': self.feedback is not None
        }

        if include_documents and self.retrieved_documents:
            data['documents'] = [doc.to_dict() for doc in self.retrieved_documents]

        return data


class RetrievedDocument(db.Model):
    """Модель документов, найденных для ответа"""
    __tablename__ = 'retrieved_documents'

    id = db.Column(db.Integer, primary_key=True)
    query_id = db.Column(db.Integer, db.ForeignKey('user_queries.id'), nullable=False)

    # Информация о документе
    document_id = db.Column(db.String(100))  # ID в базе знаний
    document_type = db.Column(db.String(50))  # lesson, rule, etc.
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    source = db.Column(db.String(200))  # Источник

    # Метрики релевантности
    relevance_score = db.Column(db.Float)  # Оценка релевантности
    rank = db.Column(db.Integer)  # Позиция в выдаче

    # Метаданные
    metadata = db.Column(JSONB, default={})

    def to_dict(self):
        return {
            'id': self.id,
            'document_id': self.document_id,
            'document_type': self.document_type,
            'title': self.title,
            'source': self.source,
            'relevance_score': self.relevance_score,
            'rank': self.rank,
            'preview': self.content[:200] + '...' if self.content else None
        }


class QueryFeedback(db.Model):
    """Модель обратной связи по ответам"""
    __tablename__ = 'query_feedback'

    id = db.Column(db.Integer, primary_key=True)
    query_id = db.Column(db.Integer, db.ForeignKey('user_queries.id'), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Оценка ответа
    rating = db.Column(db.Integer)  # 1-5 звезд
    was_helpful = db.Column(db.Boolean)

    # Детальная обратная связь
    feedback_text = db.Column(db.Text)
    categories = db.Column(JSONB, default=[])  # Массив категорий проблем/пожеланий

    # Метаданные
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'query_id': self.query_id,
            'rating': self.rating,
            'was_helpful': self.was_helpful,
            'feedback_text': self.feedback_text,
            'categories': self.categories,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ActivityLog(db.Model):
    """Модель логов активности пользователя"""
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('user_sessions.id'))

    # Тип активности
    action = db.Column(db.String(100), nullable=False)  # login, logout, query, view_page, etc.
    category = db.Column(db.String(50))  # auth, navigation, search, etc.

    # Детали
    details = db.Column(JSONB, default={})
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))

    # Время
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Индексы
    __table_args__ = (
        Index('idx_activity_user', 'user_id'),
        Index('idx_activity_created', 'created_at'),
        Index('idx_activity_action', 'action'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'category': self.category,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class KnowledgeBase(db.Model):
    """Модель базы знаний (документы)"""
    __tablename__ = 'knowledge_base'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)  # Ключ для доступа
    title = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)

    # Категоризация
    category = db.Column(db.String(50))  # lesson, rule, faq, etc.
    tags = db.Column(JSONB, default=[])  # Теги для поиска

    # Метаданные
    source = db.Column(db.String(200))
    author = db.Column(db.String(100))
    version = db.Column(db.String(20))

    # Статистика
    views_count = db.Column(db.Integer, default=0)
    queries_count = db.Column(db.Integer, default=0)

    # Временные метки
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Индексы
    __table_args__ = (
        Index('idx_kb_key', 'key'),
        Index('idx_kb_category', 'category'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'title': self.title,
            'category': self.category,
            'tags': self.tags,
            'preview': self.content[:200] + '...' if self.content else None,
            'views_count': self.views_count,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def increment_views(self):
        """Увеличение счетчика просмотров"""
        self.views_count += 1


class LearningProgress(db.Model):
    """Модель прогресса обучения студента"""
    __tablename__ = 'learning_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Прогресс по урокам
    lesson_id = db.Column(db.String(100))
    lesson_title = db.Column(db.String(200))

    # Статус
    status = db.Column(db.String(20))  # not_started, in_progress, completed
    progress_percent = db.Column(db.Integer, default=0)

    # Временные метки
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)

    # Детали
    completed_modules = db.Column(JSONB, default=[])  # Завершенные модули
    test_results = db.Column(JSONB, default={})  # Результаты тестов

    __table_args__ = (
        Index('idx_progress_user', 'user_id'),
        Index('idx_progress_status', 'status'),
        db.UniqueConstraint('user_id', 'lesson_id', name='unique_user_lesson'),
    )

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'lesson_id': self.lesson_id,
            'lesson_title': self.lesson_title,
            'status': self.status,
            'progress_percent': self.progress_percent,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None
        }


class Notification(db.Model):
    """Модель уведомлений"""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Содержание
    title = db.Column(db.String(200))
    message = db.Column(db.Text)
    type = db.Column(db.String(50))  # info, warning, success, error
    priority = db.Column(db.Integer, default=0)  # 0-10

    # Ссылки
    link = db.Column(db.String(500))
    action_data = db.Column(JSONB, default={})

    # Статус
    is_read = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False)

    # Временные метки
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    read_at = db.Column(db.DateTime)

    __table_args__ = (
        Index('idx_notification_user', 'user_id'),
        Index('idx_notification_read', 'is_read'),
        Index('idx_notification_created', 'created_at'),
    )

    def mark_as_read(self):
        """Отметить как прочитанное"""
        self.is_read = True
        self.read_at = datetime.utcnow()

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'priority': self.priority,
            'link': self.link,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }