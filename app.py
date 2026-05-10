# web_interface.py
from flask import Flask, render_template, request, jsonify
import logging
from datetime import datetime
import json
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация

from config import MY_AUTH_KEY, SCOPE

KNOWLEDGE_BASE_FILE = 'documents_with_themes.json'
WORK_TYPE = os.getenv('WORK_TYPE', 'server')  # 'server' или 'local'


# Загрузка базы знаний
def load_knowledge_base(file_path: str):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        knowledge_base = {}
        for elem in data:
            doc = list(elem.keys())[0]
            knowledge_base[doc.split("(")[0].strip()] = {'text': elem[doc]['text'],
                                      'doc_link': elem[doc]['link'],
                                      'theme': elem[doc]['theme']}


        logger.info(f"Загружено {len(knowledge_base)} документов")
        return knowledge_base
    except Exception as e:
        print(e)
        logger.error(f"Ошибка загрузки: {e}")
        return {}


KNOWLEDGE_BASE = load_knowledge_base(KNOWLEDGE_BASE_FILE)


# Функция выбора клиентов в зависимости от режима работы
def get_clients(type_work: str):
    """Возвращает клиентов в зависимости от режима работы"""
    if type_work == "server":
        from gigachat_clients import create_gigachat_clients
        clients = create_gigachat_clients(MY_AUTH_KEY, SCOPE, KNOWLEDGE_BASE)
        logger.info("Используем GigaChat клиенты")
    else:  # local
        from llama_clients import create_llama_clients
        clients = create_llama_clients(KNOWLEDGE_BASE)
        logger.info("Используем Llama клиенты")

    return clients


# Создаем клиентов при старте
clients = get_clients(WORK_TYPE)
retriever = clients["retriever"]
answer_generator = clients["answer_generator"]


@app.route('/')
def index():
    work_type = "GigaChat" if WORK_TYPE == "server" else "TinyLlama"
    return render_template('index.html',
                           work_type=work_type)


@app.route('/api/ask', methods=['POST'])
def ask_question():
    try:
        data = request.get_json()
        question = data.get('question', '').strip()

        if not question:
            return jsonify({'success': False, 'answer': 'Пустой вопрос'})

        # Выбор ключа
        # available_keys = list(KNOWLEDGE_BASE.keys())
        available_keys = list()
        # print(KNOWLEDGE_BASE)
        for elem in KNOWLEDGE_BASE:
            el = f"{elem} (desc: {KNOWLEDGE_BASE[elem]['theme']})"
            available_keys.append(el)

        selection_result = retriever.select_key(question, available_keys)
        selected_key = selection_result.get('selected_key')

        # Генерация ответа
        if selected_key and selected_key in KNOWLEDGE_BASE:
            context = KNOWLEDGE_BASE[selected_key]['text']
            doc_link = KNOWLEDGE_BASE[selected_key].get('doc_link', '')

            answer = answer_generator.generate_answer(question, context, selected_key, doc_link)

            return jsonify({
                'success': True,
                'answer': answer,
                'source': selected_key,
                'doc_link': doc_link
            })
        else:
            return jsonify({
                'success': True,
                'answer': 'Информация не найдена',
                'source': None
            })

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'work_type': WORK_TYPE,
        'kb_size': len(KNOWLEDGE_BASE)
    })


if __name__ == '__main__':
    print(f"\nРежим работы: {WORK_TYPE}")
    print(f"База знаний: {len(KNOWLEDGE_BASE)} документов\n")
    app.run(debug=True, host='0.0.0.0', port=5000)