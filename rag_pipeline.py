# rag_pipeline.py

import json
import re
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import chromadb
from sentence_transformers import SentenceTransformer
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import numpy as np


@dataclass
class RetrievedChunk:
    """Структура для хранения найденного чанка"""
    id: str
    text: str
    metadata: Dict
    distance: float
    score: float


class RAGPipeline:
    """Основной класс RAG-пайплайна"""

    def __init__(
            self,
            embedding_model_name: str = "intfloat/multilingual-e5-small",
            llm_mode: str = "gigachat",
            chroma_path: str = "./chroma_db",
            collection_name: str = "university_docs",
            top_k: int = 5,
            temperature: float = 0.2,
            gigachat_api_key: Optional[str] = None
    ):
        self.embedding_model_name = embedding_model_name
        self.llm_mode = llm_mode
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self.top_k = top_k
        self.temperature = temperature
        self.gigachat_api_key = gigachat_api_key

        self.embedding_model = None
        self.chroma_client = None
        self.collection = None
        self.llm_model = None
        self.llm_tokenizer = None

        self._load_embedding_model()
        self._load_chroma()
        self._load_llm()

    def _load_embedding_model(self):
        """Загрузка модели эмбеддингов"""
        print(f"Загрузка модели эмбеддингов: {self.embedding_model_name}")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        self.embedding_model.eval()

    def _load_chroma(self):
        """Подключение к векторной базе данных Chroma"""
        print(f"Подключение к Chroma: {self.chroma_path}")
        self.chroma_client = chromadb.PersistentClient(path=self.chroma_path)
        self.collection = self.chroma_client.get_collection(self.collection_name)
        print(f"Коллекция содержит {self.collection.count()} векторов")

    def _load_llm(self):
        """Загрузка языковой модели"""
        if self.llm_mode == "tinyllama":
            self._load_local_llm()
        elif self.llm_mode == "gigachat":
            self._load_gigachat()
        else:
            raise ValueError(f"Неизвестный режим LLM: {self.llm_mode}")

    def _load_local_llm(self):
        """Загрузка локальной модели TinyLlama"""
        print("Загрузка локальной модели TinyLlama...")
        model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

        self.llm_tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

        self.llm_model = AutoModelForCausalLM.from_pretrained(
            model_name,
            load_in_4bit=True,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True
        )
        print("Локальная модель загружена")

    def _load_gigachat(self):
        """Настройка GigaChat API"""
        print("Настройка GigaChat API")
        if not self.gigachat_api_key:
            import os
            self.gigachat_api_key = os.getenv("GIGACHAT_API_KEY", "")

        self.api_url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

    def _normalize_text(self, text: str) -> str:
        """Нормализация текста"""
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

    def _detect_doc_type(self, question: str) -> Optional[str]:
        """Автоматическое определение категории документа по ключевым словам"""
        keywords_mapping = {
            "schedule": ["расписание", "пара", "лекция", "семинар", "время занятий", "аудитория"],
            "admin": ["стипендия", "выплата", "материальная помощь", "социальная", "общежитие", "справка"],
            "regulation": ["отчисление", "перевод", "восстановление", "академический отпуск", "правила"]
        }

        question_lower = question.lower()
        for doc_type, keywords in keywords_mapping.items():
            if any(keyword in question_lower for keyword in keywords):
                return doc_type
        return None

    def _get_query_embedding(self, query: str) -> List[float]:
        """Получение эмбеддинга для запроса"""
        query_with_prefix = f"query: {self._normalize_text(query)}"
        embedding = self.embedding_model.encode(
            [query_with_prefix],
            normalize_embeddings=True
        )[0]
        return embedding.tolist()

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[RetrievedChunk]:
        """Семантический поиск релевантных чанков"""
        if top_k is None:
            top_k = self.top_k

        query_vector = self._get_query_embedding(query)

        where_filter = None
        doc_type = self._detect_doc_type(query)
        if doc_type:
            where_filter = {"doc_type": doc_type}

        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where_filter
        )

        retrieved_chunks = []
        if results['ids'] and results['ids'][0]:
            for i, chunk_id in enumerate(results['ids'][0]):
                chunk = RetrievedChunk(
                    id=chunk_id,
                    text=results['documents'][0][i],
                    metadata=results['metadatas'][0][i],
                    distance=results['distances'][0][i],
                    score=1.0 - results['distances'][0][i]
                )
                retrieved_chunks.append(chunk)

        priority_weight = lambda chunk: (1.0 / (chunk.distance + 0.001)) * chunk.metadata.get('priority', 1)
        retrieved_chunks.sort(key=priority_weight, reverse=True)

        return retrieved_chunks

    def _build_prompt(self, question: str, chunks: List[RetrievedChunk]) -> str:
        """Формирование промпта для LLM"""
        system_instruction = (
            "Ты — ИИ-консультант учебного офиса Российского экономического университета "
            "имени Г.В. Плеханова. Твоя задача — отвечать на вопросы студентов, "
            "используя ТОЛЬКО информацию из предоставленного контекста. "
            "Если ответа на вопрос нет в контексте, прямо сообщи об этом и предложи "
            "обратиться в учебный офис лично. Не используй свои собственные знания — "
            "только контекст. Отвечай на русском языке, вежливо и по делу."
        )

        context_parts = ["Вот фрагменты из документов учебного офиса:"]
        for i, chunk in enumerate(chunks, 1):
            source_name = chunk.metadata.get('doc_title', 'Неизвестный документ')
            context_parts.append(f"\n[Источник №{i}: {source_name}]\n{chunk.text}")

        context_parts.append("\nНа основе этих фрагментов ответь на вопрос студента.")
        context_parts.append(f"Если фрагменты не содержат нужной информации, сообщи об этом.")
        context_parts.append(f"\nВопрос студента: {question}")
        context_parts.append("\nОтвет:")

        if self.llm_mode == "tinyllama":
            prompt = f"{system_instruction}\n\n{chr(10).join(context_parts)}"
        else:
            prompt = f"{system_instruction}\n\n{chr(10).join(context_parts)}"

        return prompt

    def _generate_local(self, prompt: str) -> str:
        """Генерация ответа через локальную модель"""
        inputs = self.llm_tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
        inputs = {k: v.to(self.llm_model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.llm_model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=self.temperature,
                top_p=0.9,
                do_sample=True,
                pad_token_id=self.llm_tokenizer.eos_token_id
            )

        response = self.llm_tokenizer.decode(outputs[0], skip_special_tokens=True)
        response = response[len(prompt):].strip()

        return response if response else "Извините, не удалось сгенерировать ответ."

    def _generate_gigachat(self, prompt: str) -> str:
        """Генерация ответа через GigaChat API"""
        headers = {
            "Authorization": f"Bearer {self.gigachat_api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "GigaChat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": 512,
            "stream": False
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                return f"Ошибка API: {response.status_code}"
        except requests.exceptions.Timeout:
            return "Превышено время ожидания ответа от GigaChat."
        except Exception as e:
            return f"Ошибка при обращении к GigaChat: {str(e)}"

    def answer(self, question: str) -> Dict[str, Any]:
        """Основной метод получения ответа на вопрос"""

        if not question or not question.strip():
            return {
                "answer": "Пожалуйста, введите вопрос.",
                "sources": [],
                "retrieved_chunks": [],
                "success": False
            }

        retrieved_chunks = self.retrieve(question)

        if not retrieved_chunks:
            return {
                "answer": "Извините, я не нашёл информацию по вашему вопросу в документах учебного офиса. Попробуйте переформулировать запрос или обратитесь в деканат лично.",
                "sources": [],
                "retrieved_chunks": [],
                "success": False
            }

        prompt = self._build_prompt(question, retrieved_chunks)

        if self.llm_mode == "tinyllama":
            generated_answer = self._generate_local(prompt)
        else:
            generated_answer = self._generate_gigachat(prompt)

        sources = list(set([
            chunk.metadata.get('doc_title', 'Неизвестный документ')
            for chunk in retrieved_chunks
        ]))

        return {
            "answer": generated_answer,
            "sources": sources,
            "retrieved_chunks": [
                {
                    "id": chunk.id,
                    "text": chunk.text[:200],
                    "doc_title": chunk.metadata.get('doc_title'),
                    "score": chunk.score
                }
                for chunk in retrieved_chunks
            ],
            "success": True
        }


def main():
    import os
    from dotenv import load_dotenv
    load_dotenv()

    pipeline = RAGPipeline(
        embedding_model_name="intfloat/multilingual-e5-small",
        llm_mode="gigachat",
        chroma_path="./chroma_db",
        collection_name="university_docs",
        top_k=5,
        gigachat_api_key=os.getenv("GIGACHAT_API_KEY")
    )

    test_questions = [
        "Как получить академическую стипендию?",
        "Во сколько начинаются пары?",
        "Какие документы нужны для перевода?"
    ]

    for question in test_questions:
        print(f"\n{'=' * 60}")
        print(f"Вопрос: {question}")
        print('=' * 60)

        result = pipeline.answer(question)

        print(f"Ответ: {result['answer']}")
        print(f"\nИсточники: {', '.join(result['sources'])}")
        print(f"Найдено чанков: {len(result['retrieved_chunks'])}")


if __name__ == "__main__":
    main()