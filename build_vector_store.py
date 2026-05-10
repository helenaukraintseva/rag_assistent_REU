# build_vector_store.py

import json
import os
import re
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import numpy as np


class VectorStoreBuilder:
    """Класс для генерации эмбеддингов и создания векторной базы данных Chroma"""

    def __init__(
            self,
            embedding_model_name: str = "intfloat/multilingual-e5-small",
            chroma_path: str = "./chroma_db",
            batch_size: int = 32
    ):
        self.embedding_model_name = embedding_model_name
        self.chroma_path = chroma_path
        self.batch_size = batch_size
        self.model = None
        self.client = None
        self.collection = None

    def load_model(self):
        """Загрузка модели эмбеддингов"""
        print(f"Загрузка модели {self.embedding_model_name}...")
        self.model = SentenceTransformer(self.embedding_model_name)
        self.model.eval()
        print("Модель загружена")

    def load_chunks(self, json_path: str) -> List[Dict]:
        """Загрузка семантических чанков из JSON файла"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, dict) and 'chunks' in data:
            chunks = data['chunks']
        elif isinstance(data, list):
            chunks = data
        else:
            chunks = [data]

        print(f"Загружено {len(chunks)} чанков")
        return chunks

    def normalize_text(self, text: str) -> str:
        """Нормализация текста перед векторизацией"""
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

    def prepare_passages(self, chunks: List[Dict]) -> List[str]:
        """Подготовка текстов с префиксом 'passage: ' для модели E5"""
        passages = []
        for chunk in chunks:
            text = chunk.get('text', chunk.get('content', ''))
            text = self.normalize_text(text)
            passages.append(f"passage: {text}")
        return passages

    def generate_embeddings_batch(self, passages: List[str]) -> List[List[float]]:
        """Батчевая генерация эмбеддингов"""
        all_embeddings = []

        for i in range(0, len(passages), self.batch_size):
            batch = passages[i:i + self.batch_size]
            print(f"Обработка батча {i // self.batch_size + 1}/{(len(passages) - 1) // self.batch_size + 1}")

            embeddings = self.model.encode(
                batch,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            all_embeddings.extend(embeddings.tolist())

        print(f"Сгенерировано {len(all_embeddings)} эмбеддингов размерностью {len(all_embeddings[0])}")
        return all_embeddings

    def create_chroma_client(self):
        """Создание клиента Chroma с персистентным хранилищем"""
        os.makedirs(self.chroma_path, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=self.chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )
        print(f"Клиент Chroma создан, путь: {self.chroma_path}")

    def create_collection(self, collection_name: str = "university_docs"):
        """Создание коллекции в Chroma"""
        existing_collections = self.client.list_collections()
        collection_names = [col.name for col in existing_collections]

        if collection_name in collection_names:
            print(f"Коллекция {collection_name} уже существует, удаляем...")
            self.client.delete_collection(collection_name)

        self.collection = self.client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"Коллекция {collection_name} создана")
        return self.collection

    def prepare_metadata(self, chunks: List[Dict]) -> List[Dict]:
        """Подготовка метаданных для каждого чанка"""
        metadata_list = []

        for i, chunk in enumerate(chunks):
            metadata = {
                "chunk_id": chunk.get('id', f"chunk_{i}"),
                "doc_title": chunk.get('doc_title', chunk.get('title', 'unknown')),
                "doc_type": chunk.get('doc_type', chunk.get('type', 'general')),
                "chunk_index": chunk.get('chunk_index', i),
                "priority": chunk.get('priority', 1),
                "source_file": chunk.get('source_file', '')
            }
            metadata_list.append(metadata)

        return metadata_list

    def upload_to_chroma(
            self,
            chunks: List[Dict],
            embeddings: List[List[float]],
            metadata_list: List[Dict]
    ):
        """Загрузка эмбеддингов и метаданных в Chroma"""

        ids = [meta["chunk_id"] for meta in metadata_list]
        texts = [self.normalize_text(chunk.get('text', chunk.get('content', ''))) for chunk in chunks]

        print("Загрузка данных в Chroma...")

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadata_list
        )

        print(f"Загружено {len(ids)} векторов в коллекцию")

    def verify_index(self):
        """Проверка качества индексации"""
        count = self.collection.count()
        print(f"Количество векторов в коллекции: {count}")

        sample = self.collection.get(limit=5)
        if sample['ids']:
            print("\nПример загруженных данных:")
            for i, doc_id in enumerate(sample['ids'][:3]):
                metadata = sample['metadatas'][i] if sample['metadatas'] else {}
                print(f"  ID: {doc_id}")
                print(f"  Метаданные: {metadata}")
                print(f"  Текст: {sample['documents'][i][:100]}...")
                print()

    def test_search(self, test_query: str = "стипендия", top_k: int = 5):
        """Тестовый поиск для проверки работоспособности"""
        query_with_prefix = f"query: {test_query}"
        query_vector = self.model.encode([query_with_prefix], normalize_embeddings=True)[0]

        results = self.collection.query(
            query_embeddings=[query_vector.tolist()],
            n_results=top_k
        )

        print(f"\nТестовый поиск по запросу: '{test_query}'")
        print(f"Найдено результатов: {len(results['ids'][0])}")

        for i, (doc_id, metadata, distance) in enumerate(zip(
                results['ids'][0], results['metadatas'][0], results['distances'][0]
        )):
            print(f"  {i + 1}. {doc_id} (расстояние: {distance:.4f})")
            print(f"     Документ: {metadata.get('doc_title', 'unknown')}")

        return results

    def build(self, chunks_json_path: str, collection_name: str = "university_docs"):
        """Основной метод сборки векторной базы данных"""
        print("=" * 60)
        print("НАЧАЛО ПОСТРОЕНИЯ ВЕКТОРНОЙ БАЗЫ ДАННЫХ")
        print("=" * 60)

        self.load_model()

        chunks = self.load_chunks(chunks_json_path)

        passages = self.prepare_passages(chunks)

        embeddings = self.generate_embeddings_batch(passages)

        metadata_list = self.prepare_metadata(chunks)

        self.create_chroma_client()

        self.create_collection(collection_name)

        self.upload_to_chroma(chunks, embeddings, metadata_list)

        self.verify_index()

        self.test_search()

        print("\n" + "=" * 60)
        print("ВЕКТОРНАЯ БАЗА ДАННЫХ УСПЕШНО СОЗДАНА")
        print(f"Путь: {self.chroma_path}")
        print("=" * 60)

        return self.collection


def main():
    builder = VectorStoreBuilder(
        embedding_model_name="intfloat/multilingual-e5-small",
        chroma_path="./chroma_db",
        batch_size=32
    )

    builder.build(
        chunks_json_path="data/chunks.json",
        collection_name="university_docs"
    )


if __name__ == "__main__":
    main()