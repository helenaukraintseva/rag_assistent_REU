"""
rag_query_system.py - Система поиска и генерации ответов с оптимизированными параметрами
На основе экспериментов:
- top_k = 5 (оптимальное значение)
- temperature = 0.2 (для снижения галлюцинаций)
- Фильтрация по метаданным (по ключевым словам)
"""

import json
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RAGQuerySystem:
    """
    RAG система для поиска и генерации ответов
    Оптимизирована на основе экспериментальных данных
    """

    def __init__(self,
                 db_path: str = "./chroma_db_optimized",
                 embedding_model: str = "intfloat/multilingual-e5-small",
                 collection_name: str = "university_documents",
                 top_k: int = 5,  # Оптимальное значение из эксперимента
                 temperature: float = 0.2,  # Для снижения галлюцинаций
                 use_gigachat: bool = True,  # Использовать GigaChat (по умолчанию)
                 gigachat_api_key: Optional[str] = None):

        self.db_path = db_path
        self.embedding_model_name = embedding_model
        self.collection_name = collection_name
        self.top_k = top_k  # Оптимальное значение из отчета (top_k=5)
        self.temperature = temperature
        self.use_gigachat = use_gigachat

        # Загрузка компонентов
        self.embedding_model = None
        self.chroma_client = None
        self.collection = None
        self.llm_client = None

        # Кэш для категорий документов (на основе вашего отчета)
        self.category_keywords = {
            'schedule': ['расписани', 'пара', 'лекци', 'семинар', 'время заняти', 'аудитори'],
            'admin': ['стипенди', 'выплат', 'материальн помощь', 'социальн', 'академическ отпуск'],
            'regulation': ['правил', 'регламент', 'порядок', 'отчислени', 'перевод']
        }

        self._initialize_components()

    def _initialize_components(self):
        """Инициализация всех компонентов системы"""
        logger.info("Инициализация RAG системы...")

        # Загрузка модели эмбеддингов
        logger.info(f"Загрузка модели эмбеддингов: {self.embedding_model_name}")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        self.embedding_model.eval()
        self.embedding_model.to('cpu')

        # Подключение к Chroma DB
        logger.info(f"Подключение к Chroma DB: {self.db_path}")
        self.chroma_client = chromadb.PersistentClient(path=self.db_path)
        self.collection = self.chroma_client.get_collection(self.collection_name)

        logger.info(f"Коллекция загружена, содержит {self.collection.count()} чанков")

        # Инициализация LLM (опционально, для генерации ответов)
        if self.use_gigachat:
            self._init_gigachat(gigachat_api_key)

    def _init_gigachat(self, api_key: Optional[str] = None):
        """Инициализация GigaChat API"""
        try:
            import requests

            self.gigachat_api_key = api_key or self._get_gigachat_key()
            self.gigachat_url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

            # Тестовый запрос
            logger.info("GigaChat API инициализирован")

        except ImportError:
            logger.warning("Библиотека requests не установлена. GigaChat недоступен.")
            self.use_gigachat = False

    def _get_gigachat_key(self) -> Optional[str]:
        """Получение API ключа GigaChat из файла или переменных окружения"""
        import os
        # Пробуем получить из переменных окружения
        api_key = os.environ.get('GIGACHAT_API_KEY')

        # Или из файла
        if not api_key and Path('.gigachat_key').exists():
            with open('.gigachat_key', 'r') as f:
                api_key = f.read().strip()

        return api_key

    def preprocess_query(self, query: str) -> str:
        """Предобработка запроса"""
        # Очистка
        query = query.strip()

        # Добавление префикса для модели E5
        return f"query: {query}"

    def detect_doc_category(self, query: str) -> Optional[str]:
        """
        Определение категории документа по ключевым словам
        (на основе вашего подхода с фильтрацией)
        """
        query_lower = query.lower()

        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return category

        return None

    def search(self, query: str, filter_category: Optional[str] = None) -> Dict:
        """
        Семантический поиск в векторной БД

        Args:
            query: поисковый запрос
            filter_category: фильтрация по категории документа

        Returns:
            Словарь с результатами поиска
        """
        start_time = time.time()

        # Предобработка запроса
        processed_query = self.preprocess_query(query)

        # Векторизация запроса
        query_vector = self.embedding_model.encode([processed_query])[0]

        # Подготовка фильтра (на основе вашего подхода)
        where_filter = None
        if filter_category:
            where_filter = {"doc_type": filter_category}
        elif not filter_category:
            # Автоматическое определение категории
            category = self.detect_doc_category(query)
            if category:
                where_filter = {"doc_type": category}
                logger.info(f"Автоматически определена категория: {category}")

        # Поиск в Chroma
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=self.top_k,
            where=where_filter
        )

        search_time = (time.time() - start_time) * 1000  # в миллисекундах

        # Форматирование результатов
        formatted_results = {
            'query': query,
            'search_time_ms': search_time,
            'num_results': len(results['ids'][0]) if results['ids'] else 0,
            'chunks': [],
            'sources': []
        }

        if results['ids'] and results['ids'][0]:
            for i, (doc_id, document, metadata, distance) in enumerate(zip(
                    results['ids'][0],
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
            )):
                # Конвертируем расстояние в релевантность
                relevance = (1 - distance) * 100

                formatted_results['chunks'].append({
                    'id': doc_id,
                    'text': document,
                    'metadata': metadata,
                    'distance': distance,
                    'relevance': relevance
                })

                # Собираем источники
                source = {
                    'title': metadata.get('doc_title', 'Unknown'),
                    'doc_type': metadata.get('doc_type', 'unknown'),
                    'chunk_info': f"Чанк {metadata.get('chunk_index', 0) + 1}/{metadata.get('total_chunks', 1)}",
                    'relevance': relevance
                }

                if source not in formatted_results['sources']:
                    formatted_results['sources'].append(source)

        logger.info(f"Поиск выполнен за {search_time:.2f} мс, найдено {formatted_results['num_results']} результатов")

        return formatted_results

    def generate_prompt(self, query: str, search_results: Dict) -> str:
        """
        Генерация промпта для LLM (на основе вашего подхода)
        """
        if not search_results['chunks']:
            return self._get_no_results_prompt(query)

        # Системная инструкция (из вашего отчета)
        system_instruction = """Ты - ИИ-консультант учебного офиса Российского экономического университета имени Г.В. Плеханова. 
Твоя задача - отвечать на вопросы студентов, используя ТОЛЬКО информацию из предоставленного контекста. 
Если ответа на вопрос нет в контексте, прямо сообщи об этом и предложи обратиться в учебный офис лично. 
Не используй свои собственные знания - только контекст. Отвечай на русском языке, вежливо и по делу."""

        # Формирование контекста из найденных чанков
        context_parts = ["Вот фрагменты из документов учебного офиса, которые могут помочь ответить на вопрос:\n"]

        for i, chunk in enumerate(search_results['chunks'], 1):
            source_info = f"[Источник №{i}: {chunk['metadata'].get('doc_title', 'Unknown')}]"
            context_parts.append(f"{source_info}\n{chunk['text']}\n")

        context = "\n".join(context_parts)

        # Инструкция по использованию контекста
        usage_instruction = "\nНа основе этих фрагментов ответь на вопрос студента. Если фрагменты не содержат нужной информации, сообщи об этом."

        # Вопрос пользователя
        user_question = f"Вопрос студента: {query}"

        # Завершающая инструкция
        final_instruction = "\nОтвет:"

        # Сборка полного промпта
        prompt = f"{system_instruction}\n\n{context}\n{usage_instruction}\n\n{user_question}\n{final_instruction}"

        return prompt

    def _get_no_results_prompt(self, query: str) -> str:
        """Промпт для случая, когда ничего не найдено"""
        return f"""Ты - ИИ-консультант учебного офиса РЭУ им. Г.В. Плеханова.

По запросу "{query}" не найдено релевантной информации в документах учебного офиса.

Пожалуйста, ответь вежливо, что информация не найдена, и предложи:
1. Переформулировать вопрос
2. Обратиться в учебный офис лично (3 корпус, 119 кабинет)

Ответ:
"""

    def generate_answer_gigachat(self, prompt: str) -> str:
        """Генерация ответа через GigaChat API"""
        if not self.use_gigachat:
            return "GigaChat не доступен. Пожалуйста, используйте локальную версию."

        try:
            import requests

            headers = {
                "Authorization": f"Bearer {self.gigachat_api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "GigaChat",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": 512,
                "top_p": 0.9
            }

            response = requests.post(self.gigachat_url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                logger.error(f"GigaChat API ошибка: {response.status_code}")
                return "Извините, сервис временно недоступен. Пожалуйста, попробуйте позже."

        except Exception as e:
            logger.error(f"Ошибка при вызове GigaChat: {e}")
            return "Произошла ошибка при генерации ответа. Пожалуйста, попробуйте еще раз."

    def answer_question(self, query: str, filter_category: Optional[str] = None) -> Dict:
        """
        Полный цикл ответа на вопрос: поиск + генерация

        Returns:
            Словарь с ответом, источниками и метаинформацией
        """
        total_start_time = time.time()

        # Шаг 1: Поиск релевантных чанков
        search_results = self.search(query, filter_category)

        # Шаг 2: Генерация промпта
        prompt = self.generate_prompt(query, search_results)

        # Шаг 3: Генерация ответа
        if self.use_gigachat:
            answer = self.generate_answer_gigachat(prompt)
        else:
            # Можно добавить локальную генерацию
            answer = "Для генерации ответа используйте GigaChat API или настройте локальную LLM"

        total_time = time.time() - total_start_time

        # Формирование результата
        result = {
            'question': query,
            'answer': answer,
            'sources': search_results['sources'],
            'metadata': {
                'total_time_seconds': total_time,
                'search_time_ms': search_results['search_time_ms'],
                'num_chunks_used': len(search_results['chunks']),
                'top_k_used': self.top_k,
                'temperature_used': self.temperature
            }
        }

        logger.info(f"Полное время ответа: {total_time:.2f} секунд")

        return result

    def print_answer(self, result: Dict):
        """Красивый вывод ответа"""
        print("\n" + "=" * 70)
        print(f"❓ Вопрос: {result['question']}")
        print("=" * 70)
        print(f"\n💬 Ответ:\n{result['answer']}")

        if result['sources']:
            print("\n📚 Источники информации:")
            for i, source in enumerate(result['sources'], 1):
                print(
                    f"   {i}. {source['title']} ({source['doc_type']}) - {source['chunk_info']} - Релевантность: {source['relevance']:.1f}%")

        print("\n" + "=" * 70)
        print(
            f"⏱️  Время: {result['metadata']['total_time_seconds']:.2f} сек | Поиск: {result['metadata']['search_time_ms']:.0f} мс")
        print(
            f"📊 Использовано чанков: {result['metadata']['num_chunks_used']} | Top_k: {result['metadata']['top_k_used']}")
        print("=" * 70)


def interactive_mode(rag_system: RAGQuerySystem):
    """Интерактивный режим работы с системой"""
    print("\n" + "=" * 60)
    print("🤖 ИИ-КОНСУЛЬТАНТ УЧЕБНОГО ОФИСА РЭУ")
    print("=" * 60)
    print("Задайте ваш вопрос о:")
    print("  • Учёбе и расписании")
    print("  • Стипендиях и выплатах")
    print("  • Правилах перевода и отчисления")
    print("  • Документах и справках")
    print("\nВведите 'выход' для завершения, 'статистика' для информации")
    print("=" * 60)

    while True:
        query = input("\n❓ Ваш вопрос: ").strip()

        if query.lower() in ['выход', 'quit', 'exit', 'q']:
            print("👋 До свидания! Обращайтесь, если появятся вопросы.")
            break

        if query.lower() in ['статистика', 'stats']:
            print(f"\n📊 Статистика системы:")
            print(f"   • Коллекция: {rag_system.collection_name}")
            print(f"   • Всего чанков: {rag_system.collection.count()}")
            print(f"   • Top_k: {rag_system.top_k}")
            print(f"   • Temperature: {rag_system.temperature}")
            print(f"   • LLM: {'GigaChat' if rag_system.use_gigachat else 'Локальная'}")
            continue

        if not query:
            print("Пожалуйста, введите вопрос.")
            continue

        # Получение ответа
        result = rag_system.answer_question(query)
        rag_system.print_answer(result)


def main():
    """Основная функция"""

    # Конфигурация (на основе ваших экспериментов)
    CONFIG = {
        "db_path": "./chroma_db_optimized",
        "embedding_model": "intfloat/multilingual-e5-small",
        "collection_name": "university_documents",
        "top_k": 5,  # Оптимальное значение из эксперимента
        "temperature": 0.2,  # Для снижения галлюцинаций
        "use_gigachat": True  # Использовать GigaChat
    }

    # Проверка существования БД
    if not Path(CONFIG["db_path"]).exists():
        print("❌ База данных не найдена!")
        print("Сначала запустите build_vector_store.py для создания БД")
        return

    # Создание RAG системы
    rag_system = RAGQuerySystem(**CONFIG)

    # Тестовые вопросы (из вашего отчета)
    test_questions = [
        "Как получить стипендию?",
        "Каков порядок перевода на другую специальность?",
        "Что делать, если потерял студенческий билет?"
    ]

    print("\n🔍 Тестирование системы на примерах...")
    for question in test_questions:
        result = rag_system.answer_question(question)
        rag_system.print_answer(result)
        input("\nНажмите Enter для следующего вопроса...")

    # Запуск интерактивного режима
    interactive_mode(rag_system)


if __name__ == "__main__":
    main()