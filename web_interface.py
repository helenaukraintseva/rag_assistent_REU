# app.py
from flask import Flask, render_template, request, jsonify
from retriever import get_retriever
import requests
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация LLM API
LLM_API_URL = "http://195.133.40.132:8002/api/rag/context"
LLM_API_HEADERS = {"Content-Type": "application/json"}

# Инициализация ретривера
try:
    retriever = get_retriever()
    logger.info("Ретривер успешно инициализирован")

    # Проверка работоспособности
    health = retriever.health_check()
    logger.info(f"Статус ретривера: {health}")

except Exception as e:
    logger.error(f"Ошибка инициализации ретривера: {e}")
    retriever = None


class LLMClient:
    """Клиент для работы с LLM API"""

    def __init__(self, api_url: str = "http://195.133.40.132:8002/api/rag/context"):
        self.api_url = api_url

    def create_comprehensive_prompt(self, question: str, context_docs: List[Dict]) -> str:
        """Создание комплексного промпта с инструкциями и контекстом"""

        # Форматируем контекстные документы
        context_text = ""
        for i, doc in enumerate(context_docs, 1):
            source = doc.get('source', 'неизвестно')
            score = doc.get('score', 0.0)
            context_text += f"\n{'=' * 60}\n📄 ДОКУМЕНТ {i} (источник: {source}, релевантность: {score:.1%}):\n{'=' * 60}\n"
            context_text += doc.get('text', '') + "\n"

        # Создаем структурированный промпт
        prompt = f"""# ИНСТРУКЦИЯ ДЛЯ AI-АССИСТЕНТА

## РОЛЬ И КОНТЕКСТ:
Ты - AI-ассистент университетской информационной системы. Твоя задача - отвечать на вопросы студентов и сотрудников СТРОГО на основе предоставленных документов.

## ОСНОВНАЯ ЗАДАЧА:
Ответить на вопрос пользователя, используя только информацию из предоставленных документов.

## КРИТИЧЕСКИЕ ТРЕБОВАНИЯ:
1. ОТВЕЧАЙ ТОЛЬКО НА ОСНОВЕ ПРЕДОСТАВЛЕННЫХ ДОКУМЕНТОВ
2. Если в документах нет информации для ответа, скажи: "В предоставленных документах нет информации по этому вопросу"
3. НЕ придумывай информацию, которой нет в документах
4. НЕ используй свои знания вне предоставленного контекста
5. Сохраняй структуру и ключевые детали из оригинальных документов
6. Отвечай на том же языке, что и вопрос
7. Если информация противоречива, укажи на это и приведи разные варианты из документов

## ДОКУМЕНТЫ ДЛЯ АНАЛИЗА:
{context_text}

## ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{question}

## ФОРМАТ ОТВЕТА:
1. Краткий ответ на основе документов
2. Указание источников информации (из каких документов взята информация)
3. Конкретные детали и цитаты из документов (если уместно)

## НАЧНИ ОТВЕТ:"""

        return prompt

    def format_context_documents(self, context_docs: List[Dict]) -> List[Dict]:
        """Форматирование документов для API"""
        formatted_docs = []
        for i, doc in enumerate(context_docs):
            formatted_docs.append({
                "id": f"doc_{i:03d}",
                "content": doc.get("text", ""),
                "metadata": {
                    "source": doc.get("source", "unknown"),
                    "score": doc.get("score", 0.0),
                    "chunk_id": doc.get("metadata", {}).get("chunk_id", 0),
                    "original_question": doc.get("metadata", {}).get("original_query", "")
                }
            })
        return formatted_docs

    def get_response(self, question: str, context_docs: List[Dict]) -> Dict[str, Any]:
        """Получение ответа от LLM"""
        if not context_docs:
            return {
                "success": False,
                "answer": "Не найдено документов для ответа на вопрос",
                "sources": [],
                "error": "no_documents"
            }

        try:
            # Создаем комплексный промпт со всеми инструкциями
            comprehensive_prompt = self.create_comprehensive_prompt(question, context_docs)

            # Форматируем документы для API
            formatted_docs = self.format_context_documents(context_docs)

            # ⭐⭐ КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: отправляем comprehensive_prompt как question ⭐⭐
            request_data = {
                "question": comprehensive_prompt,  # Весь промпт как вопрос
                "context_documents": formatted_docs,
                "max_context_length": 3000,  # Увеличиваем для длинных промптов
                "use_rag": True
            }

            # Логирование для отладки
            logger.info(f"📤 Отправка запроса к LLM API")
            logger.info(f"📝 Длина промпта: {len(comprehensive_prompt)} символов")
            logger.info(f"📊 Документов: {len(formatted_docs)}")

            # Отправляем запрос
            response = requests.post(
                self.api_url,
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            logger.info(f"📥 Ответ LLM API: статус {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                # Обрабатываем ответ
                answer = data.get("response", "")

                # Извлекаем использованные документы
                used_doc_ids = data.get("used_documents", [])
                used_sources = []

                for doc_id in used_doc_ids:
                    try:
                        doc_num = int(doc_id.split('_')[1])
                        if doc_num < len(context_docs):
                            used_sources.append(context_docs[doc_num].get('source', 'unknown'))
                    except:
                        continue

                return {
                    "success": data.get("success", False),
                    "answer": answer,
                    "sources": used_sources if used_sources else [doc.get('source') for doc in context_docs],
                    "used_documents": used_doc_ids,
                    "response_time": 0,  # Будет заполнено позже
                    "raw_response": data
                }

            elif response.status_code == 422:
                # Пробуем упрощенный запрос
                return self._try_simplified_request(question, formatted_docs, response)
            else:
                logger.error(f"❌ Ошибка LLM API: {response.status_code} - {response.text[:200]}")
                return self._create_fallback_response(question, context_docs)

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Ошибка соединения с LLM API: {e}")
            return self._create_fallback_response(question, context_docs)
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {e}")
            return {
                "success": False,
                "answer": f"Ошибка при обработке запроса: {str(e)[:200]}",
                "sources": [],
                "error": str(e)
            }

    def _try_simplified_request(self, question: str, formatted_docs: List[Dict], original_response) -> Dict[str, Any]:
        """Попытка отправить упрощенный запрос при ошибке 422"""
        try:
            error_data = original_response.json()
            logger.warning(f"⚠️ Ошибка 422, пробую упрощенный формат: {error_data.get('detail', 'unknown')}")

            # Упрощенный запрос - только вопрос и документы
            simplified_data = {
                "question": f"Ответь на вопрос на основе документов: {question}",
                "context_documents": formatted_docs,
                "max_context_length": 2000,
                "use_rag": True
            }

            response = requests.post(
                self.api_url,
                json=simplified_data,
                headers={"Content-Type": "application/json"},
                timeout=20
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": data.get("success", False),
                    "answer": data.get("response", "Не удалось получить ответ"),
                    "sources": [doc.get('metadata', {}).get('source') for doc in formatted_docs],
                    "used_documents": data.get("used_documents", []),
                    "note": "Использован упрощенный формат запроса"
                }
            else:
                raise Exception(f"Упрощенный запрос тоже не сработал: {response.status_code}")

        except Exception as e:
            logger.error(f"❌ Упрощенный запрос не сработал: {e}")
            return self._create_fallback_response(question, formatted_docs)

    def _create_fallback_response(self, question: str, context_docs: List[Dict]) -> Dict[str, Any]:
        """Создание fallback ответа"""
        # Группируем документы по источнику
        docs_by_source = {}
        for doc in context_docs:
            source = doc.get('source', 'неизвестно')
            if source not in docs_by_source:
                docs_by_source[source] = []
            docs_by_source[source].append(doc)

        # Создаем структурированный ответ
        response_parts = []
        response_parts.append(f"# Ответ на вопрос: {question}")
        response_parts.append(
            "\n⚠️ *Примечание: LLM сервис временно недоступен. Ниже представлены найденные документы:*")

        for source, docs in docs_by_source.items():
            response_parts.append(f"\n## 📁 Источник: {source}")

            # Берем самый релевантный документ из каждого источника
            most_relevant = max(docs, key=lambda x: x.get('score', 0))
            preview = most_relevant.get('text', '')[:300]
            score = most_relevant.get('score', 0)

            response_parts.append(f"**Релевантность:** {score:.1%}")
            response_parts.append(f"**Текст:** {preview}...")

            if len(docs) > 1:
                response_parts.append(f"*(и еще {len(docs) - 1} фрагментов из этого источника)*")

        response_parts.append("\n---")
        response_parts.append("**Рекомендация:** Используйте эти документы для поиска ответа на ваш вопрос.")

        return {
            "success": True,
            "answer": "\n".join(response_parts),
            "sources": list(docs_by_source.keys()),
            "documents": context_docs,
            "note": "LLM API недоступен, показаны найденные документы"
        }

    def test_connection(self) -> Dict[str, Any]:
        """Тестирование соединения с LLM API"""
        try:
            test_docs = [{
                "id": "test_001",
                "content": "Тестовый документ для проверки соединения.",
                "metadata": {"source": "test", "type": "connection_test"}
            }]

            request_data = {
                "question": "Тестовый вопрос: работает ли соединение с API?",
                "context_documents": test_docs,
                "max_context_length": 100,
                "use_rag": True
            }

            response = requests.post(
                self.api_url,
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            return {
                "available": response.status_code == 200,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "details": response.json() if response.status_code == 200 else response.text
            }

        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "details": f"Не удалось подключиться к {self.api_url}"
            }


# Инициализация клиента LLM
llm_client = LLMClient()


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/api/ask', methods=['POST'])
def ask_question():
    """Основной API эндпоинт для вопросов с RAG"""
    if retriever is None:
        return jsonify({
            'success': False,
            'error': 'Ретривер не инициализирован',
            'answer': '',
            'documents': []
        })

    try:
        # Получаем данные
        data = request.get_json()
        if not data:
            data = request.form

        question = data.get('question', '').strip()
        k = int(data.get('k', 3))  # По умолчанию 3 документа для контекста
        threshold = float(data.get('threshold', 0.3))
        use_llm = data.get('use_llm', True)

        if not question:
            return jsonify({
                'success': False,
                'error': 'Пустой вопрос',
                'answer': '',
                'documents': []
            })

        logger.info(f"Вопрос: '{question}' (k={k}, threshold={threshold}, use_llm={use_llm})")

        # Шаг 1: Поиск релевантных документов
        search_start = datetime.now()
        search_results = retriever.search(question, k=k * 2, threshold=threshold)  # Ищем больше для фильтрации
        search_time = (datetime.now() - search_start).total_seconds()

        # Фильтруем результаты (исключаем слишком короткие или малополезные)
        filtered_results = []
        for result in search_results:
            if len(result.text.strip()) > 50:  # Минимальная длина текста
                filtered_results.append(result)
            if len(filtered_results) >= k:  # Ограничиваем количеством
                break

        # Преобразуем результаты в словари
        documents = []
        for result in filtered_results:
            documents.append({
                'text': result.text,
                'source': result.source,
                'score': float(result.score),
                'metadata': result.metadata
            })

        # Шаг 2: Получение ответа от LLM
        answer_data = {}
        llm_time = 0

        if use_llm and documents:
            llm_start = datetime.now()
            answer_data = llm_client.get_response(question, documents)
            llm_time = (datetime.now() - llm_start).total_seconds()
        elif documents:
            # Если LLM отключен, просто показываем документы
            answer_data = {
                'success': True,
                'answer': f"Найдено {len(documents)} документов. LLM отключен.",
                'sources': [doc.get('source') for doc in documents],
                'documents_preview': [doc.get('text')[:200] + '...' for doc in documents]
            }
        else:
            answer_data = {
                'success': True,
                'answer': "По вашему вопросу не найдено релевантных документов.",
                'sources': []
            }

        # Формируем итоговый ответ
        response = {
            'success': True,
            'question': question,
            'answer': answer_data.get('answer', ''),
            'sources': answer_data.get('sources', []),
            'documents': documents,
            'documents_count': len(documents),
            'search_time': search_time,
            'llm_time': llm_time if use_llm else 0,
            'total_time': search_time + llm_time,
            'used_llm': use_llm,
            'llm_success': answer_data.get('success', False)
        }

        logger.info(f"Ответ готов. Документов: {len(documents)}, Время: {response['total_time']:.2f}с")

        return jsonify(response)

    except Exception as e:
        logger.error(f"Ошибка при обработке вопроса: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'answer': '',
            'documents': []
        })


@app.route('/api/search_only', methods=['POST'])
def search_only():
    """Только поиск без LLM"""
    if retriever is None:
        return jsonify({
            'success': False,
            'error': 'Ретривер не инициализирован'
        })

    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        k = int(data.get('k', 5))
        threshold = float(data.get('threshold', 0.0))

        if not query:
            return jsonify({'success': False, 'error': 'Пустой запрос'})

        start_time = datetime.now()
        results = retriever.search(query, k=k, threshold=threshold)
        search_time = (datetime.now() - start_time).total_seconds()

        formatted_results = []
        for result in results:
            formatted_results.append({
                'text': result.text,
                'source': result.source,
                'score': float(result.score),
                'metadata': result.metadata,
                'preview': result.text[:200] + ('...' if len(result.text) > 200 else '')
            })

        return jsonify({
            'success': True,
            'query': query,
            'results': formatted_results,
            'count': len(results),
            'search_time': search_time
        })

    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/test_llm', methods=['POST'])
def test_llm():
    """Тестирование соединения с LLM API"""
    try:
        test_payload = {
            "role": "тестовый ассистент",
            "task": "ответить на тестовый вопрос",
            "requirements": ["быть кратким"],
            "input_data": "Тестовый вопрос: всё ли работает?",
            "context_documents": [{
                "id": "test_doc",
                "content": "Тестовый документ: система работает нормально.",
                "metadata": {"source": "test", "type": "test"}
            }]
        }

        response = requests.post(
            LLM_API_URL,
            json=test_payload,
            headers=LLM_API_HEADERS,
            timeout=10
        )

        return jsonify({
            'success': response.status_code == 200,
            'status_code': response.status_code,
            'response': response.json() if response.status_code == 200 else None,
            'message': 'LLM API доступен' if response.status_code == 200 else 'LLM API недоступен'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Ошибка соединения с LLM API'
        })


@app.route('/health')
def health_check():
    """Проверка состояния всей системы"""
    if retriever is None:
        return jsonify({
            'status': 'error',
            'message': 'Ретривер не инициализирован'
        })

    try:
        # Проверяем ретривер
        retriever_health = retriever.health_check()
        retriever_stats = retriever.get_index_stats()

        # Проверяем LLM API
        llm_test = test_llm()
        llm_status = llm_test.json.get('success', False)

        return jsonify({
            'status': 'ok',
            'retriever': {
                'healthy': retriever_health.get('faiss_loaded', False),
                'vectors': retriever_stats.get('total_vectors', 0),
                'metadata': retriever_stats.get('metadata_count', 0)
            },
            'llm_api': {
                'available': llm_status,
                'url': LLM_API_URL
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
    if retriever is None:
        return jsonify({'error': 'Ретривер не инициализирован'})

    stats = retriever.get_index_stats()
    return jsonify(stats)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)