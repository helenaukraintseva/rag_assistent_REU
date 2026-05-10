# tests/test_interface.py

import sys
import os
import json
import time
import threading
import requests
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class InterfaceTestResult:
    """Результат тестирования интерфейса"""
    test_name: str
    passed: bool
    execution_time_ms: float
    error_message: str = ""
    details: Dict = None


class WebInterfaceTester:
    """Класс для функционального тестирования веб-интерфейса"""

    def __init__(self, base_url: str = "http://localhost:8500"):
        self.base_url = base_url
        self.driver = None
        self.results: List[InterfaceTestResult] = []
        self.wait_timeout = 30

    def setup(self):
        """Настройка WebDriver"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')

        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)

    def teardown(self):
        """Закрытие WebDriver"""
        if self.driver:
            self.driver.quit()

    def _add_result(self, result: InterfaceTestResult):
        """Добавление результата теста"""
        self.results.append(result)
        status = "✓" if result.passed else "✗"
        print(f"{status} {result.test_name} ({result.execution_time_ms:.0f}ms)")
        if result.error_message:
            print(f"  Ошибка: {result.error_message}")

    def test_page_load(self) -> InterfaceTestResult:
        """Тест 1: Загрузка главной страницы"""
        test_name = "Загрузка главной страницы"
        start_time = time.perf_counter()

        try:
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, self.wait_timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            title = self.driver.title
            passed = "консультант" in title.lower() or "rag" in title.lower()

            return InterfaceTestResult(
                test_name=test_name,
                passed=passed,
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                details={"title": title}
            )
        except Exception as e:
            return InterfaceTestResult(
                test_name=test_name,
                passed=False,
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                error_message=str(e)
            )

    def test_input_field(self) -> InterfaceTestResult:
        """Тест 2: Наличие поля ввода вопроса"""
        test_name = "Наличие поля ввода"
        start_time = time.perf_counter()

        try:
            input_field = WebDriverWait(self.driver, self.wait_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'], textarea"))
            )

            passed = input_field is not None and input_field.is_enabled()

            return InterfaceTestResult(
                test_name=test_name,
                passed=passed,
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                details={"element_id": input_field.get_attribute("id") if input_field else None}
            )
        except Exception as e:
            return InterfaceTestResult(
                test_name=test_name,
                passed=False,
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                error_message=str(e)
            )

    def test_submit_button(self) -> InterfaceTestResult:
        """Тест 3: Наличие кнопки отправки"""
        test_name = "Наличие кнопки отправки"
        start_time = time.perf_counter()

        try:
            submit_button = WebDriverWait(self.driver, self.wait_timeout).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "button[type='submit'], input[type='submit'], button:contains('Отправить')"))
            )

            passed = submit_button is not None and submit_button.is_enabled()

            return InterfaceTestResult(
                test_name=test_name,
                passed=passed,
                execution_time_ms=(time.perf_counter() - start_time) * 1000
            )
        except Exception as e:
            return InterfaceTestResult(
                test_name=test_name,
                passed=False,
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                error_message=str(e)
            )

    def test_send_question(self, question: str, expected_keywords: List[str] = None) -> InterfaceTestResult:
        """Тест 4: Отправка вопроса и получение ответа"""
        test_name = f"Отправка вопроса: {question[:50]}..."
        start_time = time.perf_counter()

        try:
            input_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='text'], textarea")
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")

            input_field.clear()
            input_field.send_keys(question)

            submit_button.click()

            WebDriverWait(self.driver, self.wait_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".answer, .response, .message"))
            )

            time.sleep(1)

            answer_elements = self.driver.find_elements(By.CSS_SELECTOR, ".answer, .response, .message")
            answer_text = " ".join([el.text for el in answer_elements])

            passed = len(answer_text) > 10

            keywords_found = []
            if expected_keywords:
                for keyword in expected_keywords:
                    if keyword.lower() in answer_text.lower():
                        keywords_found.append(keyword)
                passed = passed and len(keywords_found) > 0

            return InterfaceTestResult(
                test_name=test_name,
                passed=passed,
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                details={
                    "answer_length": len(answer_text),
                    "keywords_found": keywords_found,
                    "answer_preview": answer_text[:200]
                }
            )
        except Exception as e:
            return InterfaceTestResult(
                test_name=test_name,
                passed=False,
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                error_message=str(e)
            )

    def test_sources_display(self, question: str) -> InterfaceTestResult:
        """Тест 5: Отображение источников ответа"""
        test_name = "Отображение источников"
        start_time = time.perf_counter()

        try:
            input_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='text'], textarea")
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")

            input_field.clear()
            input_field.send_keys(question)
            submit_button.click()

            WebDriverWait(self.driver, self.wait_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".sources, .source, .references"))
            )

            sources_elements = self.driver.find_elements(By.CSS_SELECTOR, ".sources, .source, .references")
            sources_text = " ".join([el.text for el in sources_elements])

            passed = len(sources_elements) > 0 and len(sources_text) > 0

            return InterfaceTestResult(
                test_name=test_name,
                passed=passed,
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                details={"sources_count": len(sources_elements)}
            )
        except Exception as e:
            return InterfaceTestResult(
                test_name=test_name,
                passed=False,
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                error_message=str(e)
            )

    def test_empty_question(self) -> InterfaceTestResult:
        """Тест 6: Отправка пустого вопроса"""
        test_name = "Обработка пустого вопроса"
        start_time = time.perf_counter()

        try:
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            submit_button.click()

            time.sleep(1)

            error_messages = self.driver.find_elements(By.CSS_SELECTOR, ".error, .alert, .warning")
            has_error_message = any("введите" in el.text.lower() for el in error_messages)

            passed = has_error_message

            return InterfaceTestResult(
                test_name=test_name,
                passed=passed,
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                details={"error_displayed": has_error_message}
            )
        except Exception as e:
            return InterfaceTestResult(
                test_name=test_name,
                passed=False,
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                error_message=str(e)
            )

    def test_loading_indicator(self, question: str) -> InterfaceTestResult:
        """Тест 7: Отображение индикатора загрузки"""
        test_name = "Индикатор загрузки"
        start_time = time.perf_counter()

        try:
            input_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='text'], textarea")
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")

            input_field.clear()
            input_field.send_keys(question)

            submit_button.click()

            loading_indicators = ["loading", "spinner", "loader", "загрузка"]
            found = False

            for _ in range(20):
                page_source = self.driver.page_source.lower()
                for indicator in loading_indicators:
                    if indicator in page_source:
                        found = True
                        break
                if found:
                    break
                time.sleep(0.2)

            passed = found

            return InterfaceTestResult(
                test_name=test_name,
                passed=passed,
                execution_time_ms=(time.perf_counter() - start_time) * 1000
            )
        except Exception as e:
            return InterfaceTestResult(
                test_name=test_name,
                passed=False,
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                error_message=str(e)
            )

    def test_clear_history(self) -> InterfaceTestResult:
        """Тест 8: Очистка истории диалога"""
        test_name = "Очистка истории"
        start_time = time.perf_counter()

        try:
            clear_button = self.driver.find_element(By.CSS_SELECTOR,
                                                    "button:contains('Очистить'), button:contains('Clear')")
            clear_button.click()

            time.sleep(0.5)

            messages = self.driver.find_elements(By.CSS_SELECTOR, ".message, .chat-message")

            passed = len(messages) == 0

            return InterfaceTestResult(
                test_name=test_name,
                passed=passed,
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                details={"remaining_messages": len(messages)}
            )
        except Exception as e:
            return InterfaceTestResult(
                test_name=test_name,
                passed=False,
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                error_message=str(e)
            )

    def test_responsive_layout(self) -> InterfaceTestResult:
        """Тест 9: Адаптивность интерфейса (разные разрешения)"""
        test_name = "Адаптивность интерфейса"
        start_time = time.perf_counter()

        resolutions = [(375, 667), (768, 1024), (1366, 768), (1920, 1080)]
        passed_all = True

        for width, height in resolutions:
            try:
                self.driver.set_window_size(width, height)
                time.sleep(0.5)

                body = self.driver.find_element(By.TAG_NAME, "body")
                passed_all = passed_all and body.is_displayed()

            except Exception as e:
                passed_all = False

        return InterfaceTestResult(
            test_name=test_name,
            passed=passed_all,
            execution_time_ms=(time.perf_counter() - start_time) * 1000
        )

    def test_typing_errors_handling(self) -> InterfaceTestResult:
        """Тест 10: Обработка вопросов с опечатками"""
        test_name = "Обработка опечаток"
        start_time = time.perf_counter()

        question_with_typo = "как палучить стипендию"

        try:
            input_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='text'], textarea")
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")

            input_field.clear()
            input_field.send_keys(question_with_typo)
            submit_button.click()

            WebDriverWait(self.driver, self.wait_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".answer, .response, .message"))
            )

            answer_elements = self.driver.find_elements(By.CSS_SELECTOR, ".answer, .response, .message")
            answer_text = " ".join([el.text for el in answer_elements])

            passed = len(answer_text) > 20

            return InterfaceTestResult(
                test_name=test_name,
                passed=passed,
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                details={"answer_received": len(answer_text) > 0}
            )
        except Exception as e:
            return InterfaceTestResult(
                test_name=test_name,
                passed=False,
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                error_message=str(e)
            )

    def run_all_tests(self, test_questions: List[Dict]) -> Dict:
        """Запуск всех тестов"""
        print("\n" + "=" * 60)
        print("ЗАПУСК ФУНКЦИОНАЛЬНОГО ТЕСТИРОВАНИЯ ВЕБ-ИНТЕРФЕЙСА")
        print("=" * 60 + "\n")

        self.setup()

        try:
            self.results.append(self.test_page_load())
            self.results.append(self.test_input_field())
            self.results.append(self.test_submit_button())

            if test_questions:
                first_question = test_questions[0]
                self.results.append(self.test_send_question(
                    first_question['question'],
                    first_question.get('expected_keywords', [])
                ))
                self.results.append(self.test_sources_display(first_question['question']))

            self.results.append(self.test_empty_question())

            if test_questions:
                self.results.append(self.test_loading_indicator(test_questions[0]['question']))

            self.results.append(self.test_clear_history())
            self.results.append(self.test_responsive_layout())
            self.results.append(self.test_typing_errors_handling())

        finally:
            self.teardown()

        return self.generate_report()

    def generate_report(self) -> Dict:
        """Генерация отчёта о тестировании"""

        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        report = {
            'summary': {
                'total_tests': total,
                'passed': passed,
                'failed': failed,
                'success_rate': (passed / total) * 100 if total > 0 else 0,
                'total_execution_time_ms': sum(r.execution_time_ms for r in self.results)
            },
            'test_results': [
                {
                    'name': r.test_name,
                    'passed': r.passed,
                    'time_ms': r.execution_time_ms,
                    'error': r.error_message,
                    'details': r.details
                }
                for r in self.results
            ]
        }

        self._print_report(report)

        return report

    def _print_report(self, report: Dict):
        """Вывод отчёта"""

        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТЫ ФУНКЦИОНАЛЬНОГО ТЕСТИРОВАНИЯ")
        print("=" * 60)

        summary = report['summary']
        print(f"\nВсего тестов: {summary['total_tests']}")
        print(f"Пройдено: {summary['passed']}")
        print(f"Не пройдено: {summary['failed']}")
        print(f"Успешность: {summary['success_rate']:.1f}%")
        print(f"Общее время: {summary['total_execution_time_ms']:.0f} мс")

        print("\n--- ДЕТАЛИЗАЦИЯ ---")
        for result in report['test_results']:
            status = "✓" if result['passed'] else "✗"
            print(f"{status} {result['name']} ({result['time_ms']:.0f}ms)")
            if result['error']:
                print(f"   Ошибка: {result['error']}")

        print("\n" + "=" * 60)


class APITester:
    """Класс для тестирования API эндпоинтов"""

    def __init__(self, base_url: str = "http://localhost:8500"):
        self.base_url = base_url
        self.session = requests.Session()

    def test_health_check(self) -> Tuple[bool, float]:
        """Тест health check эндпоинта"""
        start_time = time.perf_counter()

        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            latency = (time.perf_counter() - start_time) * 1000
            return response.status_code == 200, latency
        except Exception:
            return False, (time.perf_counter() - start_time) * 1000

    def test_ask_endpoint(self, question: str) -> Tuple[bool, Dict, float]:
        """Тест эндпоинта /ask"""
        start_time = time.perf_counter()

        try:
            response = self.session.post(
                f"{self.base_url}/ask",
                json={"question": question},
                timeout=30
            )
            latency = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                return True, data, latency
            else:
                return False, {"error": f"HTTP {response.status_code}"}, latency
        except Exception as e:
            return False, {"error": str(e)}, (time.perf_counter() - start_time) * 1000

    def run_api_tests(self, test_questions: List[Dict]) -> Dict:
        """Запуск всех API тестов"""
        print("\n" + "=" * 60)
        print("ЗАПУСК API ТЕСТИРОВАНИЯ")
        print("=" * 60 + "\n")

        results = []

        is_healthy, health_latency = self.test_health_check()
        results.append({
            'name': 'Health Check',
            'passed': is_healthy,
            'latency_ms': health_latency
        })
        print(f"{'✓' if is_healthy else '✗'} Health Check ({health_latency:.0f}ms)")

        for test in test_questions[:5]:
            question = test['question']
            passed, data, latency = self.test_ask_endpoint(question)

            results.append({
                'name': f"API: {question[:50]}...",
                'passed': passed,
                'latency_ms': latency,
                'has_answer': 'answer' in data if data else False
            })
            print(f"{'✓' if passed else '✗'} {question[:50]}... ({latency:.0f}ms)")

        total = len(results)
        passed = sum(1 for r in results if r['passed'])

        report = {
            'summary': {
                'total_tests': total,
                'passed': passed,
                'failed': total - passed,
                'success_rate': (passed / total) * 100 if total > 0 else 0,
                'avg_latency_ms': sum(r['latency_ms'] for r in results) / total if results else 0
            },
            'results': results
        }

        print(f"\nУспешность API: {report['summary']['success_rate']:.1f}%")
        print(f"Средняя задержка: {report['summary']['avg_latency_ms']:.0f} мс")

        return report


def main():
    """Главная функция"""

    with open("tests/test_queries.json", 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    test_questions = test_data.get('interface_tests', test_data.get('test_cases', []))

    print("ВЕБ-ИНТЕРФЕЙС ТЕСТИРОВАНИЕ")
    print("Убедитесь, что приложение запущено на http://localhost:8500\n")

    input("Нажмите Enter для запуска тестов...")

    web_tester = WebInterfaceTester(base_url="http://localhost:8500")
    web_report = web_tester.run_all_tests(test_questions)

    api_tester = APITester(base_url="http://localhost:8500")
    api_report = api_tester.run_api_tests(test_questions)

    with open("tests/interface_test_report.json", 'w', encoding='utf-8') as f:
        json.dump({
            'web_tests': web_report,
            'api_tests': api_report,
            'timestamp': time.time()
        }, f, ensure_ascii=False, indent=2)

    print("\nОтчёт сохранён в tests/interface_test_report.json")


if __name__ == "__main__":
    main()