# models.py
import json

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Модель пользователя"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    role = db.Column(db.String(20), nullable=False, default='student')  # student, teacher, admin
    faculty = db.Column(db.String(100))  # Факультет
    group = db.Column(db.String(50))  # Группа для студентов
    position = db.Column(db.String(100))  # Должность для преподавателей
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    avatar = db.Column(db.String(200), default='default-avatar.png')

    # Связи
    queries = db.relationship('UserQuery', backref='user', lazy=True, cascade='all, delete-orphan')
    sessions = db.relationship('UserSession', backref='user', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    def is_teacher(self):
        return self.role == 'teacher'

    def is_admin(self):
        return self.role == 'admin'


class UserSession(db.Model):
    """Модель сессий пользователей"""
    __tablename__ = 'user_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_token = db.Column(db.String(200), unique=True, nullable=False)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(200))
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    logout_time = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)


class KnowledgeBase(db.Model):
    """Модель базы знаний"""
    __tablename__ = 'knowledge_base'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # rules, schedule, contacts, etc.
    faculty = db.Column(db.String(100))  # Для фильтрации по факультету
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    views_count = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=True)

    # Связи
    creator = db.relationship('User', foreign_keys=[created_by])
    chunks = db.relationship('KnowledgeChunk', backref='document', lazy=True, cascade='all, delete-orphan')


class KnowledgeChunk(db.Model):
    """Чанки документов для RAG"""
    __tablename__ = 'knowledge_chunks'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('knowledge_base.id'), nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.JSON)  # Хранение эмбеддингов в JSON формате
    chunk_metadata = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Lesson(db.Model):
    """Модель уроков/занятий"""
    __tablename__ = 'lessons'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    subject = db.Column(db.String(100), nullable=False)
    faculty = db.Column(db.String(100))
    group = db.Column(db.String(50))
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    lesson_type = db.Column(db.String(50))  # lecture, practice, lab, seminar
    weekday = db.Column(db.Integer)  # 0-6 (пн-вс)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    classroom = db.Column(db.String(50))
    building = db.Column(db.String(50))
    semester = db.Column(db.Integer)
    year = db.Column(db.Integer)
    is_online = db.Column(db.Boolean, default=False)
    online_link = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи
    teacher = db.relationship('User', foreign_keys=[teacher_id])
    materials = db.relationship('LessonMaterial', backref='lesson', lazy=True)
    attendances = db.relationship('Attendance', backref='lesson', lazy=True)


class LessonMaterial(db.Model):
    """Материалы к урокам"""
    __tablename__ = 'lesson_materials'

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(500))
    file_type = db.Column(db.String(50))  # pdf, doc, ppt, video, link
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    downloads_count = db.Column(db.Integer, default=0)


class Rule(db.Model):
    """Модель правил обучения"""
    __tablename__ = 'rules'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))  # general, academic, disciplinary, scholarship
    order_index = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserQuery(db.Model):
    """Модель запросов пользователей"""
    __tablename__ = 'user_queries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    query_text = db.Column(db.Text, nullable=False)
    response_text = db.Column(db.Text)
    documents_used = db.Column(db.JSON)  # ID использованных документов
    sources = db.Column(db.JSON)  # Источники ответа
    processing_time = db.Column(db.Float)
    used_llm = db.Column(db.Boolean, default=True)
    tokens_used = db.Column(db.Integer)
    feedback_score = db.Column(db.Integer)  # 1-5 оценка пользователя
    feedback_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_sources_list(self):
        return json.loads(self.sources) if self.sources else []


class Notification(db.Model):
    """Модель уведомлений"""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50))  # info, warning, success, deadline
    link = db.Column(db.String(500))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Attendance(db.Model):
    """Модель посещаемости"""
    __tablename__ = 'attendances'

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20))  # present, absent, late, excused
    marked_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

    student = db.relationship('User', foreign_keys=[student_id])
    marker = db.relationship('User', foreign_keys=[marked_by])


class SystemLog(db.Model):
    """Модель системных логов"""
    __tablename__ = 'system_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)