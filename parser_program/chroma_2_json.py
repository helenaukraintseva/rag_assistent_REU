"""
convert_to_qa_format.py - Конвертация JSON в формат {"ключ": "текст"} с ограничением 1000 символов
"""

import json
from pathlib import Path
from typing import Dict, Any
import re


class QADataConverter:
    """Конвертер данных в формат вопрос-ответ"""

    def __init__(self, input_json_path: str, output_json_path: str = None, max_length: int = 1000):
        """
        Args:
            input_json_path: путь к входному JSON файлу
            output_json_path: путь для сохранения результата
            max_length: максимальная длина текста (по умолчанию 1000 символов)
        """
        self.input_path = Path(input_json_path)

        if output_json_path:
            self.output_path = Path(output_json_path)
        else:
            self.output_path = self.input_path.parent / f"{self.input_path.stem}_qa_format.json"

        self.max_length = max_length

    def truncate_text(self, text: str) -> str:
        """Обрезает текст до максимальной длины, сохраняя целые предложения"""
        if len(text) <= self.max_length:
            return text

        # Обрезаем до максимальной длины
        truncated = text[:self.max_length]

        # Пытаемся обрезать по границе предложения
        last_period = truncated.rfind('.')
        last_question = truncated.rfind('?')
        last_exclamation = truncated.rfind('!')
        last_space = truncated.rfind(' ')

        # Выбираем лучшую границу для обрезки
        cut_pos = max(last_period, last_question, last_exclamation, last_space)

        if cut_pos > self.max_length // 2:  # Если нашли хорошую границу
            truncated = text[:cut_pos + 1]

        # Добавляем многоточие, если текст был обрезан
        if len(truncated) < len(text):
            truncated += " ..."

        return truncated

    def clean_text(self, text: str) -> str:
        """Очистка текста от лишних пробелов и символов"""
        # Заменяем множественные пробелы на один
        text = re.sub(r'\s+', ' ', text)
        # Удаляем пробелы в начале и конце
        text = text.strip()
        return text

    def extract_document_content(self, document: str, metadata: Dict[str, Any]) -> str:
        """
        Извлекает и форматирует контент документа

        Args:
            document: текст документа
            metadata: метаданные документа

        Returns:
            Отформатированный текст
        """
        # Определяем тип документа
        doc_type = metadata.get('type', 'document')

        if doc_type == 'qa':
            # Для QA пар форматируем как вопрос-ответ
            question = metadata.get('question', '')
            answer = metadata.get('answer', '')

            if answer:
                return f"Вопрос: {question}\n\nОтвет: {answer}"
            else:
                return document
        else:
            # Для обычных документов
            doc_name = metadata.get('document_name', metadata.get('doc_title', 'Документ'))

            # Убираем размер файла из названия, если есть
            doc_name = re.sub(r'\s*\([\d.]+\s*[МК]б\.\)\s*', '', doc_name)
            doc_name = doc_name.strip()

            return f"Документ: {doc_name}\n\n{document}"

    def get_document_key(self, metadata: Dict[str, Any]) -> str:
        """
        Получает ключ для документа (название или вопрос)

        Returns:
            Ключ для JSON
        """
        doc_type = metadata.get('type', 'document')

        if doc_type == 'qa':
            # Для QA пар используем вопрос как ключ
            return metadata.get('question', 'unknown_question')
        else:
            # Для обычных документов используем название
            doc_name = metadata.get('document_name', metadata.get('doc_title', 'unknown_document'))
            # Убираем размер файла из названия
            doc_name = re.sub(r'\s*\([\d.]+\s*[МК]б\.\)\s*', '', doc_name)
            doc_name = doc_name.strip()
            return doc_name

    def convert(self) -> Dict[str, str]:
        """
        Конвертирует JSON в формат {"ключ": "текст"}

        Returns:
            Словарь с данными
        """
        print(f"\n📖 Загрузка данных из {self.input_path}")

        # Загружаем исходный JSON
        with open(self.input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"   Найдено документов: {len(data.get('documents', []))}")

        result = {}
        stats = {
            'total': len(data.get('documents', [])),
            'qa_pairs': 0,
            'regular_docs': 0,
            'truncated': 0,
            'skipped': 0
        }

        print(f"\n🔄 Обработка документов (макс. длина: {self.max_length} символов)")
        print("-" * 60)

        for idx, (doc_id, document, metadata) in enumerate(zip(
                data.get('ids', []),
                data.get('documents', []),
                data.get('metadatas', [])
        ), 1):

            # Получаем ключ (название документа или вопрос)
            key = self.get_document_key(metadata)

            # Пропускаем дубликаты
            if key in result:
                print(f"   ⚠️ [{idx}/{stats['total']}] Дубликат ключа: {key[:50]}...")
                stats['skipped'] += 1
                continue

            # Форматируем контент
            content = self.extract_document_content(document, metadata)

            # Очищаем текст
            content = self.clean_text(content)

            # Обрезаем до максимальной длины
            original_length = len(content)
            if original_length > self.max_length:
                content = self.truncate_text(content)
                stats['truncated'] += 1

            # Сохраняем в результат
            result[key] = content

            # Статистика по типу
            if metadata.get('type') == 'qa':
                stats['qa_pairs'] += 1
            else:
                stats['regular_docs'] += 1

            # Выводим прогресс
            status = "✂️ обрезан" if original_length > self.max_length else "✅"
            print(f"   {status} [{idx}/{stats['total']}] {key[:40]}... ({original_length} -> {len(content)} симв.)")

        # Сохраняем результат
        print(f"\n💾 Сохранение в {self.output_path}")
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # Выводим статистику
        print("\n" + "=" * 60)
        print("📊 СТАТИСТИКА КОНВЕРТАЦИИ")
        print("=" * 60)
        print(f"Всего обработано: {stats['total']}")
        print(f"  • QA пары: {stats['qa_pairs']}")
        print(f"  • Обычные документы: {stats['regular_docs']}")
        print(f"  • Обрезано документов: {stats['truncated']}")
        print(f"  • Пропущено (дубликаты): {stats['skipped']}")
        print(f"\nРазмер выходного файла: {self.output_path.stat().st_size / 1024:.2f} KB")
        print(f"Количество записей: {len(result)}")
        print("=" * 60)

        return result

    def print_sample(self, num_samples: int = 3):
        """Выводит примеры из сконвертированного файла"""
        if not self.output_path.exists():
            print("Файл не найден. Сначала запустите convert()")
            return

        with open(self.output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print("\n" + "=" * 60)
        print(f"📝 ПРИМЕРЫ ЗАПИСЕЙ (первые {num_samples})")
        print("=" * 60)

        for i, (key, value) in enumerate(list(data.items())[:num_samples], 1):
            print(f"\n{i}. Ключ: {key}")
            print(f"   Текст: {value[:200]}..." if len(value) > 200 else f"   Текст: {value}")
            print(f"   Длина: {len(value)} символов")

    def export_to_markdown(self, markdown_path: str = None):
        """Экспортирует данные в Markdown формат для удобного просмотра"""
        if not self.output_path.exists():
            print("Файл не найден. Сначала запустите convert()")
            return

        if not markdown_path:
            markdown_path = self.output_path.with_suffix('.md')

        with open(self.output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write("# База знаний учебного офиса\n\n")
            f.write(f"Всего записей: {len(data)}\n\n")
            f.write("---\n\n")

            for i, (key, value) in enumerate(data.items(), 1):
                f.write(f"## {i}. {key}\n\n")
                f.write(f"{value}\n\n")
                f.write(f"*Длина: {len(value)} символов*\n\n")
                f.write("---\n\n")

        print(f"\n✅ Экспортировано в Markdown: {markdown_path}")


def convert_json_with_options():
    """Утилита для конвертации с различными опциями"""

    # Параметры конвертации
    INPUT_FILE = "chroma_data_with_qa.json"
    OUTPUT_FILE = "qa_format_database.json"
    MAX_LENGTH = 1000  # Максимальная длина текста

    # Проверяем существование файла
    if not Path(INPUT_FILE).exists():
        print(f"❌ Файл {INPUT_FILE} не найден!")

        # Ищем другие JSON файлы
        json_files = list(Path(".").glob("*.json"))
        if json_files:
            print("\n📁 Найденные JSON файлы:")
            for i, f in enumerate(json_files, 1):
                print(f"   {i}. {f.name}")

            choice = input("\nВыберите файл (номер) или нажмите Enter для выхода: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(json_files):
                INPUT_FILE = json_files[int(choice) - 1].name
                print(f"✅ Выбран файл: {INPUT_FILE}")
            else:
                return
        else:
            return

    # Создаем конвертер
    converter = QADataConverter(
        input_json_path=INPUT_FILE,
        output_json_path=OUTPUT_FILE,
        max_length=MAX_LENGTH
    )

    # Конвертируем
    result = converter.convert()

    # Показываем примеры
    converter.print_sample(num_samples=3)

    # Предлагаем экспорт в Markdown
    export_md = input("\n📝 Экспортировать в Markdown? (y/N): ").strip().lower()
    if export_md == 'y':
        converter.export_to_markdown()

    print(f"\n✅ Готово! Файл сохранен как: {OUTPUT_FILE}")
    print(f"   Формат: {{'название_документа': 'текст'}}")
    print(f"   Максимальная длина текста: {MAX_LENGTH} символов")


# Альтернативная версия с фильтрацией по типу документа
class FilteredQADataConverter(QADataConverter):
    """Конвертер с возможностью фильтрации по типу документа"""

    def __init__(self, input_json_path: str, output_json_path: str = None,
                 max_length: int = 1000, include_types: list = None):
        """
        Args:
            include_types: список типов документов для включения ('qa', 'pdf', 'document' и т.д.)
        """
        super().__init__(input_json_path, output_json_path, max_length)
        self.include_types = include_types or ['qa', 'pdf', 'document']

    def convert_filtered(self) -> Dict[str, str]:
        """Конвертирует только документы определенных типов"""

        print(f"\n📖 Загрузка данных из {self.input_path}")
        print(f"   Фильтр: включаем типы {self.include_types}")

        with open(self.input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        result = {}
        stats = {
            'total': len(data.get('documents', [])),
            'filtered_out': 0,
            'included': 0,
            'truncated': 0
        }

        for idx, (doc_id, document, metadata) in enumerate(zip(
                data.get('ids', []),
                data.get('documents', []),
                data.get('metadatas', [])
        ), 1):

            doc_type = metadata.get('type', 'document')

            # Фильтрация по типу
            if doc_type not in self.include_types:
                stats['filtered_out'] += 1
                continue

            # Получаем ключ
            key = self.get_document_key(metadata)

            if key in result:
                continue

            # Форматируем контент
            content = self.extract_document_content(document, metadata)
            content = self.clean_text(content)

            if len(content) > self.max_length:
                content = self.truncate_text(content)
                stats['truncated'] += 1

            result[key] = content
            stats['included'] += 1

            if stats['included'] % 10 == 0:
                print(f"   Обработано: {stats['included']} документов")

        # Сохраняем результат
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 60)
        print("📊 СТАТИСТИКА (с фильтрацией)")
        print("=" * 60)
        print(f"Всего документов в исходном JSON: {stats['total']}")
        print(f"Отфильтровано (неподходящий тип): {stats['filtered_out']}")
        print(f"Включено в результат: {stats['included']}")
        print(f"Из них обрезано до {self.max_length} символов: {stats['truncated']}")
        print("=" * 60)

        return result


def main():
    """Основная функция"""
    print("=" * 60)
    print("🔄 КОНВЕРТОР JSON В ФОРМАТ ВОПРОС-ОТВЕТ")
    print("=" * 60)

    print("\nВыберите режим работы:")
    print("1. Стандартная конвертация (все документы)")
    print("2. Конвертация только QA пар")
    print("3. Конвертация только PDF документов")
    print("4. Конвертация с пользовательскими настройками")

    choice = input("\nВаш выбор (1-4): ").strip()

    INPUT_FILE = "chroma_data_with_qa.json"
    OUTPUT_FILE = "qa_format_database.json"
    MAX_LENGTH = 1000

    if not Path(INPUT_FILE).exists():
        # Поиск других JSON файлов
        json_files = list(Path(".").glob("*.json"))
        if json_files:
            print(f"\n⚠️ Файл {INPUT_FILE} не найден.")
            print("Доступные JSON файлы:")
            for i, f in enumerate(json_files, 1):
                print(f"  {i}. {f.name}")
            file_choice = input("\nВыберите файл (номер): ").strip()
            if file_choice.isdigit() and 1 <= int(file_choice) <= len(json_files):
                INPUT_FILE = json_files[int(file_choice) - 1].name
            else:
                print("❌ Неверный выбор")
                return
        else:
            print(f"❌ Файл {INPUT_FILE} не найден и нет других JSON файлов")
            return

    if choice == '1':
        # Стандартная конвертация
        converter = QADataConverter(INPUT_FILE, OUTPUT_FILE, MAX_LENGTH)
        result = converter.convert()
        converter.print_sample(3)

    elif choice == '2':
        # Только QA пары
        output_qa = "qa_pairs_only.json"
        converter = FilteredQADataConverter(INPUT_FILE, output_qa, MAX_LENGTH, include_types=['qa'])
        result = converter.convert_filtered()

    elif choice == '3':
        # Только PDF документы
        output_pdf = "pdf_documents_only.json"
        converter = FilteredQADataConverter(INPUT_FILE, output_pdf, MAX_LENGTH, include_types=['pdf', 'document'])
        result = converter.convert_filtered()

    elif choice == '4':
        # Пользовательские настройки
        print("\nНастройки конвертации:")
        custom_length = input(f"Максимальная длина текста (по умолчанию {MAX_LENGTH}): ").strip()
        if custom_length.isdigit():
            MAX_LENGTH = int(custom_length)

        custom_output = input(f"Имя выходного файла (по умолчанию {OUTPUT_FILE}): ").strip()
        if custom_output:
            OUTPUT_FILE = custom_output

        converter = QADataConverter(INPUT_FILE, OUTPUT_FILE, MAX_LENGTH)
        result = converter.convert()
        converter.print_sample(5)

    else:
        print("❌ Неверный выбор")
        return

    print("\n✅ Программа завершена!")


if __name__ == "__main__":
    main()