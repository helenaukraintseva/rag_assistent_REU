# RAG QA Система с векторным поиском и LLM

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-active-success.svg)]()
[![RAG System](https://img.shields.io/badge/architecture-RAG-orange.svg)]()

Полноценная система вопрос-ответов на основе RAG (Retrieval-Augmented Generation), объединяющая векторный поиск документов и языковые модели для точных и контекстуальных ответов.

## 🌟 Основные возможности

- **📚 Поддержка множества форматов**: TXT, PDF, DOCX
- **🔍 Семантический поиск**: Поиск по смыслу с использованием векторных эмбеддингов
- **🤖 Интеграция с LLM**: Поддержка Gemini API и других языковых моделей
- **⚡ Две векторные БД**: Поддержка ChromaDB и FAISS
- **🌐 Веб-интерфейс**: Современный интерфейс для взаимодействия
- **📊 Мониторинг**: Статистика и мониторинг работы системы

## 🏗️ Архитектура системы
```
┌─────────────────┐       ┌─────────────────┐      ┌─────────────────┐
│ Документы       │ ───▶ │   Векторная БД  │ ───▶ │   Поисковый     │
│ (TXT/PDF/DOCX)  │       │ (ChromaDB/FAISS)│      │    движок       │
└─────────────────┘       └─────────────────┘      └─────────────────┘

┌─────────────────┐    ┌─────────────────┐      ┌─────────▼─────────┐
│ Пользователь    │◀───│ Веб-интерфейс  │ ◀─── │ LLM-сервис        │
│     (Flask)     │    │    (Gemini API) │      │                   │
└─────────────────┘    └─────────────────┘      └───────────────────┘
```
📁 Структура проекта

```
rag_assistant/
├── app.py                        # Главный файл веб-интерфейса (Flask)
├── rag_pipeline.py               # Класс RAGPipeline (основная логика)
├── build_vector_store.py         # Скрипт для генерации эмбеддингов и создания Chroma DB
├── config.py                     # Конфигурации (параметры, API-ключи, пути)
├── requirements.txt              # Зависимости проекта
├── .env                          # Переменные окружения (API-ключи, не в git)
├── chroma_db/                    # Директория с векторной БД (создаётся автоматически)
│   └── (файлы индексов Chroma)
├── data/                         # Исходные данные
│   └── chunks.json               # Семантические чанки с метаданными (результат предыдущего этапа)
├── static/                       # Статические файлы для веб-интерфейса
│   ├── style.css                 # Кастомные стили (опционально)
│   └── script.js                 # Клиентская логика (опционально)
├── templates/                    # HTML-шаблоны Flask
│   └── index.html                # Главная страница чата
├── utils/                        # Вспомогательные модули
│   ├── __init__.py
│   ├── text_processing.py        # Нормализация, исправление опечаток, префиксы (query:/passage:)
│   ├── metadata_filters.py       # Авто-определение категории по ключевым словам
│   └── metrics.py                # Метрики качества (precision@k, recall@k и т.д.)
├── models/                       # Работа с моделями
│   ├── __init__.py
│   ├── embedding_model.py        # Загрузка intfloat/multilingual-e5-small
│   └── llm_wrapper.py            # Абстракция для TinyLlama (локально) и GigaChat (API)
└── tests/                        # Тестирование
    ├── test_retrieval.py         # Проверка семантического поиска
    ├── test_pipeline.py          # Интеграционные тесты RAG-пайплайна
    ├── test_interface.py         # Функциональное тестирование веб-интерфейса
    └── test_queries.json         # 20-25 тестовых запросов из отчёта
```


## 🔧 Установка

### 1. Клонирование репозитория
```bash
git clone <repository-url>
cd rag-qa-system
```
### 2. Установка зависимостей
```bash
pip install -r requirements.txt
```
### 3. Настройка конфигурации
Создайте файл config.py на основе примера:

```python
# config.py
import os
from pathlib import Path

class Config:
    # Пути к данным
    RAW_DATA_DIR = Path("data/raw")
    OUTPUT_DIR = Path("outputs")
    
    # Настройки обработки текста
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50
    
    # Модель для эмбеддингов
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    DEVICE = "cpu"  # или "cuda"
    
    # Настройки LLM
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "ваш-api-ключ")
```

### 4. Подготовка данных
Поместите документы в формате TXT, PDF или DOCX в директорию data/raw/

## 🚀 Быстрый старт
### Вариант 1: Использование ChromaDB (рекомендуется)
Построение векторной базы данных:

```bash
python build_vector_db.py
```
Запуск веб-интерфейса:
```bash
python web_interface.py
```
Откройте в браузере: http://localhost:5000

### Вариант 2: Использование FAISS
Используйте существующие скрипты для FAISS или сконвертируйте в ChromaDB:

```bash
python migrate_faiss_to_chromadb.py
```

### Вариант 3: Запуск LLM API сервера
Для использования с Gemini API:

```bash
python program_2.py
```
Сервер запустится на http://localhost:8002

## 📡 API Эндпоинты

### Веб-интерфейс (Flask сервер - порт 5000)

| Метод | Эндпоинт | Описание | Параметры запроса |
|-------|----------|----------|-------------------|
| **GET** | `/` | Главная страница с веб-интерфейсом | - |
| **POST** | `/api/ask` | Основной эндпоинт для вопросов с RAG | `question` (string), `k` (int, default=3), `threshold` (float, default=0.3), `use_llm` (bool, default=True) |
| **POST** | `/api/search_only` | Поиск документов без генерации ответа | `query` (string), `k` (int, default=5), `threshold` (float, default=0.0) |
| **POST** | `/api/test_llm` | Тестирование соединения с LLM API | - |
| **GET** | `/health` | Проверка состояния системы | - |
| **GET** | `/stats` | Статистика векторной БД | - |

### LLM API сервер (FastAPI - порт 8002)

| Метод | Эндпоинт | Описание | Пример тела запроса |
|-------|----------|----------|-------------------|
| **GET** | `/` | Информация о сервере | - |
| **GET** | `/health` | Проверка здоровья сервера | - |
| **POST** | `/api/simple` | Простой текстовый промпт | `{"question": "Ваш вопрос здесь"}` |
| **POST** | `/api/structured` | Структурированный промпт | `{"role": "эксперт", "task": "объяснить тему", "requirements": "быть кратким", "input_data": "что такое ИИ?"}` |
| **POST** | `/api/detailed` | Детализированный промпт | `{"role_context": "эксперт по ML", "main_task": "объяснить нейросети", "requirements": ["просто", "с примерами"], "input_data": "что такое CNN?"}` |
| **POST** | `/api/rag/context` | RAG с готовым контекстом | `{"question": "Ваш вопрос", "context_documents": [{"id": "doc1", "content": "текст документа", "metadata": {"source": "файл.txt"}}], "use_rag": true}` |

## 🔍 Использование
### Через веб-интерфейс
1. Откройте http://localhost:5000
2. Введите вопрос в текстовое поле
3. Настройте параметры поиска (количество документов, порог релевантности)

4. Нажмите "Получить ответ"

### Через API
```python
import requests

response = requests.post("http://localhost:5000/api/ask", 
    json={
        "question": "Какое расписание занятий?",
        "k": 3,
        "threshold": 0.3,
        "use_llm": True
    }
)
```
## ⚙️ Конфигурация
Основные параметры в config.py:
- **CHUNK_SIZE** - Размер фрагментов текста (по умолчанию: 500)

- **CHUNK_OVERLAP** - Перекрытие между фрагментами (по умолчанию: 50)

- **EMBEDDING_MODEL** - Модель для создания эмбеддингов

- **DEVICE** - Используемое устройство (cpu/cuda)

- **GEMINI_API_KEY** - API ключ для Gemini

Переменные окружения:
```bash
export GEMINI_API_KEY="ваш-api-ключ"
export SEARCH_SERVICE_URL="http://localhost:8001"
```
## 🧪 Тестирование
Проверка ретривера:
```bash
python check_retriever.py
```
Тестирование LLM API:
```bash
python program_1_check.py
```
Проверка системы:
```bash
# Проверка здоровья
curl http://localhost:5000/health
# Получение статистики
curl http://localhost:5000/stats
```
## 📊 Мониторинг
Система предоставляет:

- Статистику поисковых запросов

- Количество документов в базе

- Время обработки запросов

- Состояние LLM API

- Информацию о загруженных моделях

## 🔄 Миграция между базами данных
Из FAISS в ChromaDB:
```bash
python migrate_faiss_to_chromadb.py
```
## 🚨 Устранение неполадок
Ошибка: "ChromaDB не инициализирован"
```bash
# Проверьте наличие файлов базы данных
ls outputs/chroma_db/

# Перестройте базу данных
python build_vector_db.py
```
Ошибка: "LLM API недоступен"
```bash
# Проверьте запущен ли LLM сервер
curl http://localhost:8002/health

# Запустите сервер
python program_2.py
```
Ошибка: "Модель не загружена"
```bash
# Проверьте наличие модели
pip install sentence-transformers

# Используйте более легкую модель в config.py
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
```
## 🛠️ Расширение функциональности
- Добавление новых форматов документов
- Редактируйте document_loader.py для поддержки новых форматов.

- Использование других LLM
- Измените program_2.py для подключения других API (OpenAI, Anthropic и др.).

- Кастомные промпты
- Настройте промпты в web_interface.py в классе LLMClient.

## 📈 Производительность
Рекомендации:
- Используйте GPU для обработки больших объемов документов

- Настройте размер батчей в зависимости от доступной памяти

- Используйте кэширование частых запросов

- Регулярно обновляйте векторную базу при добавлении новых документов

## 🤝 Вклад в проект
- Форкните репозиторий

- Создайте ветку для новой функциональности

- Внесите изменения

- Протестируйте работу

- Создайте pull request

## 📄 Лицензия
Проект распространяется под лицензией MIT.

## 📞 Поддержка
По вопросам использования и проблемам создавайте issues в репозитории.


## 🚀 Начните использовать RAG QA систему уже сегодня!

