# tests/test_pipeline.py

import sys
import os
import json
import time
import asyncio
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_pipeline import RAGPipeline
from config import Config


@dataclass
class TestResult:
    """Результат тестирования одного запроса"""
    question: str
    expected_answer_keywords: List[str]
    generated_answer: str
    sources: List[str]
    expert_score: float
    has_hallucination: bool
    sources_correct: bool
    latency_seconds: float
    retrieval_count: int


class PipelineTester:
    """Класс для тестирования RAG-пайплайна"""

    def __init__(self, pipeline: RAGPipeline):
        self.pipeline = pipeline
        self.results: List[TestResult] = []

    def load_test_suite(self, test_file_path: str) -> Dict:
        """Загрузка тестового набора с экспертными оценками"""
        with open(test_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data

    def run_tests(self, test_suite: Dict, llm_mode: str = None) -> List[TestResult]:
        """Запуск тестирования пайплайна"""

        if llm_mode:
            self.pipeline.llm_mode = llm_mode
            self.pipeline._load_llm()

        for test_case in test_suite['test_cases']:
            question = test_case['question']
            expected_keywords = test_case.get('expected_keywords', [])
            expected_sources = test_case.get('expected_sources', [])

            start_time = time.perf_counter()
            response = self.pipeline.answer(question)
            latency = time.perf_counter() - start_time

            expert_score = self._simulate_expert_evaluation(
                response['answer'],
                expected_keywords
            )

            has_hallucination = self._check_hallucination(
                response['answer'],
                response['sources']
            )

            sources_correct = self._verify_sources(
                response['sources'],
                expected_sources
            )

            result = TestResult(
                question=question,
                expected_answer_keywords=expected_keywords,
                generated_answer=response['answer'],
                sources=response['sources'],
                expert_score=expert_score,
                has_hallucination=has_hallucination,
                sources_correct=sources_correct,
                latency_seconds=latency,
                retrieval_count=len(response.get('retrieved_chunks', []))
            )

            self.results.append(result)
            self._print_progress(len(self.results), len(test_suite['test_cases']))

        return self.results

    def _simulate_expert_evaluation(self, answer: str, keywords: List[str]) -> float:
        """Симуляция экспертной оценки (1-5) на основе ключевых слов"""
        if not keywords:
            return 4.0

        answer_lower = answer.lower()
        found_keywords = sum(1 for kw in keywords if kw.lower() in answer_lower)
        score = 1 + (found_keywords / len(keywords)) * 4
        return min(5.0, max(1.0, score))

    def _check_hallucination(self, answer: str, sources: List[str]) -> bool:
        """Проверка наличия галлюцинаций (информации не из источников)"""

        hallucination_markers = [
            "я думаю", "по моему мнению", "возможно также",
            "согласно моим данным", "обычно", "как правило"
        ]

        for marker in hallucination_markers:
            if marker.lower() in answer.lower():
                if not any(source in answer for source in sources):
                    return True

        return False

    def _verify_sources(self, response_sources: List[str], expected_sources: List[str]) -> bool:
        """Проверка корректности указания источников"""
        if not expected_sources:
            return len(response_sources) > 0

        response_set = set(response_sources)
        expected_set = set(expected_sources)

        if expected_set.intersection(response_set):
            return True

        return False

    def _print_progress(self, current: int, total: int):
        """Вывод прогресса тестирования"""
        percent = (current / total) * 100
        bar_length = 30
        filled = int(bar_length * current // total)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"\rПрогресс: |{bar}| {percent:.1f}% ({current}/{total})", end='', flush=True)

    def calculate_metrics(self) -> Dict:
        """Расчёт метрик качества пайплайна"""

        if not self.results:
            return {}

        scores = [r.expert_score for r in self.results]
        hallucinations = [1 if r.has_hallucination else 0 for r in self.results]
        sources_ok = [1 if r.sources_correct else 0 for r in self.results]
        latencies = [r.latency_seconds for r in self.results]

        return {
            'overall_metrics': {
                'mean_expert_score': sum(scores) / len(scores),
                'median_expert_score': sorted(scores)[len(scores) // 2],
                'hallucination_rate': sum(hallucinations) / len(hallucinations),
                'sources_accuracy': sum(sources_ok) / len(sources_ok),
                'total_tests': len(self.results)
            },
            'latency_metrics': {
                'mean_latency_seconds': sum(latencies) / len(latencies),
                'median_latency_seconds': sorted(latencies)[len(latencies) // 2],
                'min_latency_seconds': min(latencies),
                'max_latency_seconds': max(latencies)
            },
            'score_distribution': {
                'score_5': sum(1 for s in scores if s >= 4.5),
                'score_4': sum(1 for s in scores if 3.5 <= s < 4.5),
                'score_3': sum(1 for s in scores if 2.5 <= s < 3.5),
                'score_below_3': sum(1 for s in scores if s < 2.5)
            }
        }

    def compare_llm_configs(self, test_suite: Dict, llm_configs: List[str]) -> Dict:
        """Сравнение разных LLM (локальная vs облачная)"""

        comparison_results = {}

        for llm_mode in llm_configs:
            print(f"\n\nТестирование LLM: {llm_mode}")
            self.results = []
            self.run_tests(test_suite, llm_mode=llm_mode)
            comparison_results[llm_mode] = self.calculate_metrics()

        return comparison_results

    def compare_top_k_values(self, test_suite: Dict, k_values: List[int]) -> Dict:
        """Сравнение разных значений top_k"""

        comparison_results = {}

        for k in k_values:
            print(f"\n\nТестирование top_k = {k}")
            self.pipeline.top_k = k
            self.results = []
            self.run_tests(test_suite)
            comparison_results[f'top_{k}'] = self.calculate_metrics()

        return comparison_results

    def print_detailed_report(self):
        """Вывод детального отчёта по каждому тестовому запросу"""

        print("\n" + "=" * 80)
        print("ДЕТАЛЬНЫЙ ОТЧЁТ ПО ТЕСТИРОВАНИЮ RAG-ПАЙПЛАЙНА")
        print("=" * 80)

        for i, result in enumerate(self.results, 1):
            print(f"\n--- Тест #{i} ---")
            print(f"Вопрос: {result.question[:100]}...")
            print(f"Оценка эксперта: {result.expert_score:.1f}/5.0")
            print(f"Галлюцинации: {'ДА' if result.has_hallucination else 'нет'}")
            print(f"Источники корректны: {'ДА' if result.sources_correct else 'нет'}")
            print(f"Время ответа: {result.latency_seconds:.2f} сек")
            print(f"Найдено чанков: {result.retrieval_count}")
            print(f"Источники: {', '.join(result.sources[:3])}")

            if result.has_hallucination:
                print(f"Ответ: {result.generated_answer[:200]}...")

    def print_summary_report(self):
        """Вывод сводного отчёта"""

        metrics = self.calculate_metrics()

        print("\n" + "=" * 60)
        print("СВОДНЫЙ ОТЧЁТ ПО ТЕСТИРОВАНИЮ")
        print("=" * 60)

        print("\n--- ОЦЕНКА КАЧЕСТВА ---")
        om = metrics['overall_metrics']
        print(f"  Средняя экспертная оценка: {om['mean_expert_score']:.2f}/5.0")
        print(f"  Медианная экспертная оценка: {om['median_expert_score']:.2f}/5.0")
        print(f"  Доля галлюцинаций: {om['hallucination_rate'] * 100:.1f}%")
        print(f"  Точность указания источников: {om['sources_accuracy'] * 100:.1f}%")
        print(f"  Всего тестов: {om['total_tests']}")

        print("\n--- РАСПРЕДЕЛЕНИЕ ОЦЕНОК ---")
        sd = metrics['score_distribution']
        print(f"  Отлично (5): {sd['score_5']}")
        print(f"  Хорошо (4): {sd['score_4']}")
        print(f"  Удовлетворительно (3): {sd['score_3']}")
        print(f"  Ниже 3: {sd['score_below_3']}")

        print("\n--- ПРОИЗВОДИТЕЛЬНОСТЬ ---")
        lm = metrics['latency_metrics']
        print(f"  Среднее время: {lm['mean_latency_seconds']:.2f} сек")
        print(f"  Медианное время: {lm['median_latency_seconds']:.2f} сек")
        print(f"  Минимальное время: {lm['min_latency_seconds']:.2f} сек")
        print(f"  Максимальное время: {lm['max_latency_seconds']:.2f} сек")

        print("\n" + "=" * 60)

    def export_results(self, output_file: str):
        """Экспорт результатов в JSON"""

        export_data = {
            'results': [asdict(r) for r in self.results],
            'metrics': self.calculate_metrics(),
            'config': {
                'embedding_model': self.pipeline.embedding_model_name,
                'llm_mode': self.pipeline.llm_mode,
                'top_k': self.pipeline.top_k
            }
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        print(f"\nРезультаты экспортированы в {output_file}")


def main():
    from rag_pipeline import RAGPipeline
    from config import Config

    print("=" * 60)
    print("ТЕСТИРОВАНИЕ RAG-ПАЙПЛАЙНА")
    print("=" * 60)

    print("\nИнициализация RAG-пайплайна...")
    pipeline = RAGPipeline(
        embedding_model_name="intfloat/multilingual-e5-small",
        llm_mode="gigachat",
        chroma_path="./chroma_db",
        top_k=5
    )

    tester = PipelineTester(pipeline)

    test_suite = tester.load_test_suite("tests/test_queries.json")

    print(f"\nЗагружен тестовый набор: {len(test_suite['test_cases'])} тестов")

    print("\nЗапуск тестирования...")
    tester.run_tests(test_suite)

    tester.print_summary_report()

    tester.print_detailed_report()

    tester.export_results("tests/test_results.json")

    print("\nСравнение LLM (локальная vs GigaChat)...")
    comparison = tester.compare_llm_configs(
        test_suite,
        llm_configs=["tinyllama", "gigachat"]
    )

    for llm, metrics in comparison.items():
        print(f"\n{llm}:")
        print(f"  Средняя оценка: {metrics['overall_metrics']['mean_expert_score']:.2f}")
        print(f"  Галлюцинации: {metrics['overall_metrics']['hallucination_rate'] * 100:.1f}%")
        print(f"  Среднее время: {metrics['latency_metrics']['mean_latency_seconds']:.2f} сек")


if __name__ == "__main__":
    main()