# web_interface.py
from flask import Flask, render_template, request, jsonify
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import re

from langchain_gigachat.chat_models import GigaChat
from langchain_core.messages import SystemMessage
from config import auto_key

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация GigaChat
giga = GigaChat(
    credentials=auto_key,
    verify_ssl_certs=False,
    temperature=0.7
)

# Структурированные данные в формате JSON (ключ -> информация)
STRUCTURED_DATA = {
    "university_rules": {
        "title": "Правила университета",
        "description": "Общие правила обучения и поведения в университете",
        "content": {
            "attendance_rule": "Посещение занятий обязательно",
            "absence_limit": "Допускается пропуск не более 20% занятий",
            "scholarship_conditions": "Стипендия назначается при успешной сдаче сессии",
            "academic_leave": "Академический отпуск предоставляется по медицинским показаниям",
            "additional_rules": [
                "Соблюдение академической этики",
                "Выполнение учебного плана в установленные сроки",
                "Своевременная сдача зачетов и экзаменов"
            ]
        }
    },
    "class_schedule": {
        "title": "Расписание занятий",
        "description": "Расписание занятий для групп",
        "content": {
            "group_pro_42": {
                "group_name": "ПРО-42",
                "schedule": {
                    "monday": "9:00-10:30 Математика (ауд. 301)",
                    "tuesday": "10:45-12:15 Программирование (ауд. 415)",
                    "wednesday": "14:00-15:30 Базы данных (ауд. 302)"
                },
                "group_leader": {
                    "name": "Иванов Иван",
                    "phone": "8-900-123-45-67",
                    "email": "i.ivanov@university.edu"
                },
                "additional_info": "Расписание может изменяться. Актуальная информация на доске объявлений"
            },
            "general_schedule_rules": [
                "Занятия начинаются в соответствии с расписанием",
                "Опоздание более чем на 15 минут считается пропуском",
                "Перенос занятий возможен по согласованию с деканатом"
            ]
        }
    },
    "academic_process": {
        "title": "Учебный процесс",
        "description": "Организация учебного процесса",
        "content": {
            "session_periods": [
                "Зимняя сессия: декабрь-январь",
                "Летняя сессия: май-июнь"
            ],
            "grading_system": "5-балльная система: 5 (отлично), 4 (хорошо), 3 (удовлетворительно), 2 (неудовлетворительно)",
            "retake_policy": "Пересдача неудовлетворительных оценок осуществляется в установленные сроки",
            "thesis_work": {
                "deadlines": "Защита дипломных работ проводится в конце учебного года",
                "requirements": "Объем: 50-70 страниц, наличие практической части"
            }
        }
    },
    "student_life": {
        "title": "Студенческая жизнь",
        "description": "Внеучебная деятельность и сервисы",
        "content": {
            "student_organizations": [
                "Студенческий совет",
                "Научное общество студентов",
                "Спортивные секции",
                "Творческие коллективы"
            ],
            "campus_facilities": [
                "Библиотека (работает 9:00-20:00)",
                "Спортивный комплекс",
                "Студенческая столовая",
                "Медицинский пункт"
            ],
            "dormitory_info": {
                "availability": "Предоставляется иногородним студентам",
                "cost": "1500 рублей в месяц",
                "requirements": "Заявление подается в деканате"
            }
        }
    },
    "contacts_and_support": {
        "title": "Контакты и поддержка",
        "description": "Контактная информация и службы поддержки",
        "content": {
            "dean_office": {
                "phone": "+7 (XXX) XXX-XX-XX",
                "email": "dekanat@university.edu",
                "hours": "Пн-Пт 9:00-17:00",
                "location": "Главный корпус, каб. 101"
            },
            "study_department": {
                "phone": "+7 (XXX) XXX-XX-XX",
                "email": "uchebniy@university.edu",
                "responsibilities": "Вопросы учебного плана, расписания, переводов"
            },
            "technical_support": {
                "phone": "+7 (XXX) XXX-XX-XX",
                "email": "support@university.edu",
                "services": "Помощь с электронным университетом, Wi-Fi, техника"
            },
            "emergency_contacts": [
                "Охрана: 2222 (внутренний)",
                "Медицинская помощь: 3333 (внутренний)",
                "Психологическая поддержка: +7 (XXX) XXX-XX-XX"
            ]
        }
    },
    "admissions": {
        "title": "Поступление",
        "description": "Информация для абитуриентов",
        "content": {
            "admission_dates": {
                "start": "20 июня",
                "end": "26 июля",
                "documents_deadline": "10 августа"
            },
            "required_documents": [
                "Аттестат о среднем образовании",
                "Паспорт",
                "Фотографии 3x4 (4 шт.)",
                "Медицинская справка 086/у",
                "Заявление о приеме"
            ],
            "entrance_exams": [
                "Математика (профильный)",
                "Русский язык",
                "Информатика/Физика (по выбору)"
            ],
            "passing_scores": {
                "budget": "от 240 баллов",
                "paid": "от 160 баллов"
            }
        }
    },
}


class IntelligentAssistant:
    """Интеллектуальный ассистент с использованием GigaChat"""

    def __init__(self):
        pass

    def _call_gigachat(self, prompt: str) -> str:
        """Вызов GigaChat с обработкой ошибок"""
        try:
            response = giga.invoke([SystemMessage(content=prompt)])
            return response.content.strip()
        except Exception as e:
            logger.error(f"Ошибка GigaChat: {e}")
            raise

    def classify_question_to_key(self, question: str) -> Dict[str, Any]:
        """
        Определяет, к какому ключу из STRUCTURED_DATA относится вопрос
        """
        prompt = f"""
        Анализируй вопрос пользователя и определи, к какой категории он относится.

        Доступные категории (ключи) и их описание:
        1. university_rules - правила университета, посещение, пропуски, стипендии
        2. class_schedule - расписание занятий, аудитории, время пар
        3. academic_process - учебный процесс, сессии, оценки, дипломные работы
        4. student_life - студенческая жизнь, общежития, внеучебная деятельность
        5. contacts_and_support - контакты деканата, техподдержка, экстренные службы
        6. admissions - поступление, документы, экзамены, проходные баллы

        Вопрос пользователя: "{question}"

        Требования:
        - Ответь ТОЛЬКО в формате JSON
        - Используй точные ключи из списка выше, если данных нет, так и пиши "У меня нет соответствующей информации"
        - Если вопрос относится к нескольким категориям, выбери самую релевантную
        - Если вопрос не относится ни к одной категории, используй "university_rules"
        - Нельзя выбирать темы не из доступных категорий
        - confidence должен отражать процентную вероятность ответа
        - Если вопрос не относится ни к одной из предложенных категорий, то confidence приравняй к 0

        Формат ответа:
        {{
            "primary_key": "название_ключа",
            "confidence": 0.95,
            "explanation": "краткое объяснение выбора",
            "alternative_keys": ["дополнительный_ключ1", "дополнительный_ключ2"]
        }}

        Ответ:
        """

        try:
            response_text = self._call_gigachat(prompt)

            # Пытаемся найти JSON в ответе
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                classification = json.loads(json_match.group())

                return classification
            else:
                # Пробуем спарсить весь ответ как JSON
                try:
                    classification = json.loads(response_text)
                    return classification
                except:
                    # Fallback
                    return self._fallback_classification(question)

        except Exception as e:
            logger.error(f"Ошибка классификации: {e}")
            return self._fallback_classification(question)

    def _fallback_classification(self, question: str) -> Dict[str, Any]:
        """Fallback классификация по ключевым словам"""
        question_lower = question.lower()

        keyword_mapping = {
            "university_rules": ["правила", "посещение", "пропуск", "стипендия", "отпуск", "обязательно"],
            "class_schedule": ["расписание", "график", "пара", "аудитория", "занятие", "время"],
            "academic_process": ["сессия", "экзамен", "зачет", "оценка", "диплом", "учебный"],
            "student_life": ["общежитие", "столовая", "секция", "внеучебный", "досуг"],
            "contacts_and_support": ["контакт", "деканат", "поддержка", "телефон", "адрес", "помощь"],
            "admissions": ["поступление", "абитуриент", "документ", "экзамен", "балл", "прием"]
        }

        scores = {}
        for key, keywords in keyword_mapping.items():
            score = sum(1 for keyword in keywords if keyword in question_lower)
            scores[key] = score

        # Выбираем ключ с максимальным score
        if max(scores.values()) == 0:
            primary_key = "university_rules"
            confidence = 0.0
        else:
            primary_key = max(scores.items(), key=lambda x: x[1])[0]
            confidence = scores[primary_key] / len(keyword_mapping[primary_key]) if keyword_mapping[primary_key] else 0

        return {
            "primary_key": primary_key,
            "confidence": confidence,
            "explanation": f"Определено по ключевым словам: {', '.join(keyword_mapping[primary_key][:3])}",
            "alternative_keys": []
        }

    def generate_response(self, question: str, data_key: str) -> Dict[str, Any]:
        """
        Генерирует ответ на основе вопроса и данных по ключу
        """
        if data_key not in STRUCTURED_DATA:
            data_key = "university_rules"

        data = STRUCTURED_DATA[data_key]

        prompt = f"""
        Ты - AI-ассистент университета. Ответь на вопрос студента используя ТОЛЬКО предоставленные данные.

        Контекстные данные ({data['title']} - {data['description']}):
        {json.dumps(data['content'], ensure_ascii=False, indent=2)}

        Вопрос студента: "{question}"

        Требования к ответу:
        1. Используй ТОЛЬКО информацию из предоставленных данных, 
        2. Если данных нет, напиши только "У меня нет соответствующей информации" и закончи сообщение
        3. Будь дружелюбным и профессиональным 👨‍🎓
        4. Используй маркированные списки для перечислений
        5. Добавь эмодзи для лучшего восприятия 📚🎓🏛️
        6. Если информации недостаточно, вежливо сообщи об этом и предложи уточнить вопрос
        7. В конце предложи связанные темы или задай уточняющий вопрос
        8. Пиши по-русски! Это очень важно!

        Формат ответа:
        - Приветствие и понимание вопроса
        - Основной ответ на основе данных
        - Дополнительная информация (если есть)
        - Предложение дальнейшей помощи

        Ответ:
        """

        try:
            answer = self._call_gigachat(prompt)

            return {
                "success": True,
                "answer": answer,
                "data_key": data_key,
                "data_title": data["title"],
                "sources": [data_key],
                "model_used": "GigaChat"
            }

        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            return self._generate_fallback_response(question, data)

    def _generate_fallback_response(self, question: str, data: Dict) -> Dict[str, Any]:
        """Fallback генерация ответа"""
        response_parts = []
        response_parts.append(f"## {data['title']} 📚")
        response_parts.append(f"*{data['description']}*")
        response_parts.append("")

        # Простое форматирование данных
        content = data['content']
        for key, value in content.items():
            if isinstance(value, list):
                response_parts.append(f"**{key.replace('_', ' ').title()}:**")
                for item in value:
                    response_parts.append(f"• {item}")
            elif isinstance(value, dict):
                response_parts.append(f"**{key.replace('_', ' ').title()}:**")
                for subkey, subvalue in value.items():
                    if isinstance(subvalue, dict):
                        for k, v in subvalue.items():
                            response_parts.append(f"  - {k}: {v}")
                    else:
                        response_parts.append(f"  - {subkey}: {subvalue}")
            else:
                response_parts.append(f"**{key.replace('_', ' ').title()}:** {value}")

        response_parts.append("")
        response_parts.append("---")
        response_parts.append(
            "ℹ️ Это автоматически сгенерированный ответ на основе структурированных данных университета.")

        return {
            "success": True,
            "answer": "\n".join(response_parts),
            "data_key": list(STRUCTURED_DATA.keys())[list(STRUCTURED_DATA.values()).index(data)],
            "data_title": data["title"],
            "sources": [list(STRUCTURED_DATA.keys())[list(STRUCTURED_DATA.values()).index(data)]],
            "note": "Сгенерировано через fallback (GigaChat недоступен)"
        }

    def get_structured_data_overview(self) -> Dict[str, Any]:
        """Возвращает обзор структурированных данных"""
        overview = {}
        for key, data in STRUCTURED_DATA.items():
            overview[key] = {
                "title": data["title"],
                "description": data["description"],
                "content_keys": list(data["content"].keys()),
                "content_types": {k: type(v).__name__ for k, v in data["content"].items()}
            }
        return overview


# Инициализация ассистента
assistant = IntelligentAssistant()


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/api/ask', methods=['POST'])
def ask_question():
    """Основной API эндпоинт для вопросов"""
    try:
        # Получаем данные
        data = request.get_json()
        if not data:
            data = request.form

        question = data.get('question', '').strip()

        if not question:
            return jsonify({
                'success': False,
                'error': 'Пустой вопрос',
                'answer': ''
            })

        logger.info(f"Вопрос: '{question}'")

        start_time = datetime.now()

        # Шаг 1: Классификация вопроса
        classification_start = datetime.now()
        classification = assistant.classify_question_to_key(question)
        print(f"CLASS_1___{classification}____")
        classification_time = (datetime.now() - classification_start).total_seconds()

        # Шаг 2: Генерация ответа на основе классификации
        generation_start = datetime.now()
        # if classification['confidence'] > 0.8:
        #     key = classification["primary_key"]
        # else:
        #     key = "no_data"
        response_data = assistant.generate_response(question, classification["primary_key"])
        generation_time = (datetime.now() - generation_start).total_seconds()

        total_time = (datetime.now() - start_time).total_seconds()

        # Формируем итоговый ответ
        result = {
            'success': True,
            'question': question,
            'answer': response_data.get('answer', ''),
            'classification': classification,
            'data_source': {
                'key': response_data.get('data_key'),
                'title': response_data.get('data_title'),
                'sources': response_data.get('sources', [])
            },
            'timing': {
                'classification_time': classification_time,
                'generation_time': generation_time,
                'total_time': total_time
            },
            'metadata': {
                'structured_data_keys': list(STRUCTURED_DATA.keys()),
                'response_method': 'ai_subquery',
                'model_used': 'GigaChat'
            }
        }

        logger.info(f"Ответ готов. Категория: {classification['primary_key']}, Время: {total_time:.2f}с")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Ошибка при обработке вопроса: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'answer': ''
        })


@app.route('/api/classify', methods=['POST'])
def classify_only():
    """Только классификация вопроса"""
    try:
        data = request.get_json()
        question = data.get('question', '').strip()

        if not question:
            return jsonify({'success': False, 'error': 'Пустой вопрос'})

        start_time = datetime.now()
        classification = assistant.classify_question_to_key(question)
        print(f"CLASS_2___{classification}____")
        processing_time = (datetime.now() - start_time).total_seconds()

        # Добавляем информацию о доступных данных для этого ключа
        if classification["primary_key"] in STRUCTURED_DATA:
            data_info = STRUCTURED_DATA[classification["primary_key"]]
            classification["data_available"] = {
                "title": data_info["title"],
                "description": data_info["description"],
                "content_keys": list(data_info["content"].keys())
            }

        return jsonify({
            'success': True,
            'question': question,
            'classification': classification,
            'processing_time': processing_time,
            'all_categories': [
                {"key": key, "title": data["title"], "description": data["description"]}
                for key, data in STRUCTURED_DATA.items()
            ]
        })

    except Exception as e:
        logger.error(f"Ошибка классификации: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/data', methods=['GET'])
def get_structured_data():
    """Получение структурированных данных"""
    try:
        key = request.args.get('key', None)

        if key:
            if key in STRUCTURED_DATA:
                return jsonify({
                    'success': True,
                    'key': key,
                    'data': STRUCTURED_DATA[key]
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Ключ "{key}" не найден',
                    'available_keys': list(STRUCTURED_DATA.keys())
                })
        else:
            # Возвращаем все ключи с кратким описанием
            overview = {}
            for key, data in STRUCTURED_DATA.items():
                overview[key] = {
                    "title": data["title"],
                    "description": data["description"],
                    "content_keys": list(data["content"].keys())
                }

            return jsonify({
                'success': True,
                'data_overview': overview,
                'total_keys': len(STRUCTURED_DATA)
            })

    except Exception as e:
        logger.error(f"Ошибка получения данных: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/test_llm', methods=['POST'])
def test_llm():
    """Тестирование GigaChat"""
    try:
        test_prompt = "Тестовый вопрос: всё ли работает? Ответь кратко."
        response = giga.invoke([SystemMessage(content=test_prompt)])

        return jsonify({
            'success': True,
            'gigachat_available': True,
            'test_response': response.content[:100],
            'model': 'GigaChat',
            'message': 'GigaChat работает корректно'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'gigachat_available': False,
            'error': str(e),
            'message': 'Ошибка подключения к GigaChat'
        })


@app.route('/health')
def health_check():
    """Проверка состояния всей системы"""
    try:
        # Проверяем GigaChat
        try:
            test_response = giga.invoke([SystemMessage(content="Тест")])
            gigachat_ok = len(test_response.content) > 0
        except:
            gigachat_ok = False

        # Проверяем структурированные данные
        data_status = {
            'total_keys': len(STRUCTURED_DATA),
            'keys': list(STRUCTURED_DATA.keys()),
            'data_integrity': all(
                'title' in data and 'description' in data and 'content' in data
                for data in STRUCTURED_DATA.values()
            )
        }

        return jsonify({
            'status': 'ok' if gigachat_ok else 'warning',
            'system': 'university_assistant_with_gigachat',
            'gigachat': {
                'available': gigachat_ok,
                'model': 'GigaChat'
            },
            'structured_data': data_status,
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
    stats = {
        'structured_data': {
            'total_categories': len(STRUCTURED_DATA),
            'categories': [
                {
                    'key': key,
                    'title': data['title'],
                    'content_items': len(data['content']),
                    'content_types': {
                        k: type(v).__name__
                        for k, v in data['content'].items()
                    }
                }
                for key, data in STRUCTURED_DATA.items()
            ]
        },
        'model_info': {
            'name': 'GigaChat',
            'temperature': 0.7,
            'response_method': 'ai_subquery_classification'
        }
    }
    return jsonify(stats)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)