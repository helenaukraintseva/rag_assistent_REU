# tests/test_retrieval.py

import sys
import os
import json
import time
import numpy as np
from typing import List, Dict, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_pipeline import RAGPipeline
from utils.metrics import precision_at_k, recall_at_k, mrr_at_k, ndcg_at_k


class RetrievalTester:
    """Класс для тестирования качества семантического поиска"""

    def __init__(self, pipeline: RAGPipeline):
        self.pipeline = pipeline
        self.results = []

    def load_test_queries(self, test_file_path: str) -> List[Dict]:
        """Загрузка тестовых запросов с разметкой релевантности"""
        with open(test_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['queries']

    def evaluate_retrieval(self, queries: List[Dict], k_values: List[int] = [3, 5, 7]) -> Dict:
        """Оценка качества поиска по метрикам precision@k, recall@k, mrr@k, ndcg@k"""

        metrics_summary = {k: {'precision': [], 'recall': [], 'mrr': [], 'ndcg': []} for k in k_values}

        for query_data in queries:
            question = query_data['question']
            relevant_chunk_ids = set(query_data['relevant_chunk_ids'])

            retrieved_chunks = self.pipeline.retrieve(question, top_k=max(k_values))
            retrieved_ids = [chunk['id'] for chunk in retrieved_chunks]

            for k in k_values:
                retrieved_k = retrieved_ids[:k]

                precision = precision_at_k(retrieved_k, relevant_chunk_ids, k)
                recall = recall_at_k(retrieved_k, relevant_chunk_ids, len(relevant_chunk_ids))
                mrr = mrr_at_k(retrieved_k, relevant_chunk_ids, k)
                ndcg = ndcg_at_k(retrieved_k, relevant_chunk_ids, k)

                metrics_summary[k]['precision'].append(precision)
                metrics_summary[k]['recall'].append(recall)
                metrics_summary[k]['mrr'].append(mrr)
                metrics_summary[k]['ndcg'].append(ndcg)

            self.results.append({
                'question': question,
                'retrieved_ids': retrieved_ids[:7],
                'relevant_ids': list(relevant_chunk_ids)
            })

        final_metrics = {}
        for k in k_values:
            final_metrics[k] = {
                'precision@k': np.mean(metrics_summary[k]['precision']),
                'recall@k': np.mean(metrics_summary[k]['recall']),
                'mrr@k': np.mean(metrics_summary[k]['mrr']),
                'ndcg@k': np.mean(metrics_summary[k]['ndcg'])
            }

        return final_metrics

    def test_search_latency(self, queries: List[Dict], num_runs: int = 5) -> Dict:
        """Тестирование времени выполнения поиска"""
        latencies = []

        for query_data in queries[:10]:
            question = question = query_data['question']

            for _ in range(num_runs):
                start_time = time.perf_counter()
                self.pipeline.retrieve(question, top_k=5)
                latency = (time.perf_counter() - start_time) * 1000
                latencies.append(latency)

        return {
            'mean_latency_ms': np.mean(latencies),
            'median_latency_ms': np.median(latencies),
            'p95_latency_ms': np.percentile(latencies, 95),
            'p99_latency_ms': np.percentile(latencies, 99),
            'min_latency_ms': np.min(latencies),
            'max_latency_ms': np.max(latencies)
        }

    def compare_embedding_models(self, queries: List[Dict], models: List[str], k: int = 5) -> Dict:
        """Сравнение разных моделей эмбеддингов"""
        results = {}

        for model_name in models:
            self.pipeline.embedding_model_name = model_name
            self.pipeline._load_embedding_model()

            metrics = self.evaluate_retrieval(queries, k_values=[k])
            results[model_name] = metrics[k]

            print(f"\nМодель: {model_name}")
            print(f"  precision@{k}: {metrics[k]['precision@k']:.4f}")
            print(f"  recall@{k}: {metrics[k]['recall@k']:.4f}")
            print(f"  mrr@{k}: {metrics[k]['mrr@k']:.4f}")

        return results

    def print_report(self, metrics: Dict):
        """Вывод отчёта о тестировании"""
        print("\n" + "=" * 60)
        print("ОТЧЁТ ПО ТЕСТИРОВАНИЮ СЕМАНТИЧЕСКОГО ПОИСКА")
        print("=" * 60)

        for k, values in metrics.items():
            print(f"\n--- top_{k} ---")
            print(f"  Precision@{k}: {values['precision@k']:.4f}")
            print(f"  Recall@{k}:    {values['recall@k']:.4f}")
            print(f"  MRR@{k}:       {values['mrr@k']:.4f}")
            print(f"  NDCG@{k}:      {values['ndcg@k']:.4f}")

        print("\n" + "=" * 60)


def main():
    from rag_pipeline import RAGPipeline
    from config import Config

    print("Загрузка RAG-пайплайна...")
    pipeline = RAGPipeline(
        embedding_model_name="intfloat/multilingual-e5-small",
        llm_mode="gigachat",
        chroma_path="./chroma_db"
    )

    tester = RetrievalTester(pipeline)

    test_queries = tester.load_test_queries("tests/test_queries.json")

    print(f"\nЗагружено {len(test_queries)} тестовых запросов")

    metrics = tester.evaluate_retrieval(test_queries, k_values=[3, 5, 7])

    tester.print_report(metrics)

    latency_stats = tester.test_search_latency(test_queries)
    print(f"\nСтатистика времени поиска:")
    print(f"  Среднее: {latency_stats['mean_latency_ms']:.2f} мс")
    print(f"  Медиана: {latency_stats['median_latency_ms']:.2f} мс")
    print(f"  P95: {latency_stats['p95_latency_ms']:.2f} мс")


if __name__ == "__main__":
    main()