# manage.py
from flask import Flask
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from extensions import db
from models import *
import os

app = Flask(__name__)
app.config.from_object('config.DevelopmentConfig')

db.init_app(app)
migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)


@manager.command
def seed():
    """Заполнение базы данных тестовыми данными"""
    from datetime import date

    # Создание тестовых групп
    groups = [
        Group(name='ИТ-201', faculty='Информационные технологии', course=2, department='Прикладная информатика'),
        Group(name='ИТ-202', faculty='Информационные технологии', course=2, department='Прикладная информатика'),
        Group(name='ПМ-101', faculty='Прикладная математика', course=1, department='Высшая математика'),
    ]

    for group in groups:
        db.session.add(group)

    db.session.commit()

    # Создание тестовых пользователей
    users = [
        User(
            username='ivanov',
            email='ivanov@university.ru',
            first_name='Иван',
            last_name='Иванов',
            student_id='STU001',
            group_id=1,
            course=2,
            faculty='Информационные технологии',
            is_verified=True,
            role='student'
        ),
        User(
            username='petrova',
            email='petrova@university.ru',
            first_name='Мария',
            last_name='Петрова',
            student_id='STU002',
            group_id=1,
            course=2,
            faculty='Информационные технологии',
            is_verified=True,
            role='student'
        ),
        User(
            username='sidorov',
            email='sidorov@university.ru',
            first_name='Петр',
            last_name='Сидоров',
            student_id='STU003',
            group_id=2,
            course=2,
            faculty='Информационные технологии',
            is_verified=True,
            role='student'
        ),
    ]

    for user in users:
        user.set_password('password123')
        db.session.add(user)

    db.session.commit()

    # Создание тестовых запросов
    queries = [
        UserQuery(
            user_id=1,
            question='Какое расписание на понедельник?',
            answer='В понедельник в 9:00 математика в ауд. 301',
            query_type='general',
            confidence=0.95,
            used_llm=True,
            response_time=1.2
        ),
        UserQuery(
            user_id=1,
            question='Правила сдачи экзаменов',
            answer='Для допуска к экзамену нужно сдать все лабораторные работы',
            query_type='rules',
            confidence=0.88,
            used_llm=True,
            response_time=0.8
        ),
    ]

    for query in queries:
        db.session.add(query)

    db.session.commit()

    print("База данных успешно заполнена тестовыми данными!")


if __name__ == '__main__':
    manager.run()