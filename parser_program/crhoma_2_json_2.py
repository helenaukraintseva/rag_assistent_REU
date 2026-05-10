"""
convert_to_qa_format.py - Конвертация JSON в формат
{"answer/theme": {"text": "...", "doc_link": "..."}, ...}
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional


class EnhancedQADataConverter:
    """
    Конвертер данных в формат с текстом и ссылками на документы
    Формат: {"ключ": {"text": "текст", "doc_link": "ссылка"}, ...}
    """

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
            self.output_path = self.input_path.parent / f"{self.input_path.stem}_with_links.json"

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

    def extract_doc_link(self, metadata: Dict[str, Any]) -> str:
        """
        Извлекает ссылку на документ из метаданных

        Returns:
            Ссылка на документ или пустая строка
        """
        # Проверяем разные возможные поля со ссылками
        link_fields = ['pdf_link', 'doc_link', 'link', 'url', 'source_link']

        for field in link_fields:
            if field in metadata and metadata[field]:
                return metadata[field]

        # Для QA пар ссылки может не быть
        if metadata.get('type') == 'qa':
            return ""

        return ""

    def format_content_with_link(self, content: str, link: str) -> str:
        """
        Форматирует контент, добавляя ссылку в текст (если есть)
        Для большей информативности
        """
        if not link:
            return content

        # Добавляем ссылку в начало текста
        return f"[Источник: {link}]\n\n{content}"

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
                formatted = f"Вопрос: {question}\n\nОтвет: {answer}"
            else:
                formatted = document

            return formatted
        else:
            # Для обычных документов
            doc_name = metadata.get('document_name', metadata.get('doc_title', 'Документ'))

            # Убираем размер файла из названия, если есть
            doc_name = re.sub(r'\s*\([\d.]+\s*[МК]б\.\)\s*', '', doc_name)
            doc_name = doc_name.strip()

            formatted = f"Документ: {doc_name}\n\n{document}"

            return formatted

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

    def convert(self) -> Dict[str, Dict[str, str]]:
        """
        Конвертирует JSON в формат {"ключ": {"text": "текст", "doc_link": "ссылка"}}

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
            'with_links': 0,
            'without_links': 0,
            'truncated': 0,
            'skipped': 0
        }

        print(f"\n🔄 Обработка документов (макс. длина текста: {self.max_length} символов)")
        print("-" * 70)

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

            # Получаем ссылку на документ
            doc_link = self.extract_doc_link(metadata)

            # Форматируем контент
            content = self.extract_document_content(document, metadata)

            # Очищаем текст
            content = self.clean_text(content)

            # Обрезаем до максимальной длины
            original_length = len(content)
            if original_length > self.max_length:
                content = self.truncate_text(content)
                stats['truncated'] += 1

            # Сохраняем в результат в новом формате
            result[key] = {
                "text": content,
                "doc_link": doc_link
            }

            # Статистика по типу
            if metadata.get('type') == 'qa':
                stats['qa_pairs'] += 1
                stats['without_links'] += 1  # У QA пар обычно нет ссылок
            else:
                stats['regular_docs'] += 1
                if doc_link:
                    stats['with_links'] += 1
                else:
                    stats['without_links'] += 1

            # Выводим прогресс
            status = "✂️ обрезан" if original_length > self.max_length else "✅"
            link_status = "🔗" if doc_link else "📄"
            print(
                f"   {status} {link_status} [{idx}/{stats['total']}] {key[:40]}... ({original_length} -> {len(content)} симв.)")

        # Сохраняем результат
        print(f"\n💾 Сохранение в {self.output_path}")
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # Выводим статистику
        print("\n" + "=" * 70)
        print("📊 СТАТИСТИКА КОНВЕРТАЦИИ")
        print("=" * 70)
        print(f"Всего обработано: {stats['total']}")
        print(f"  • QA пары: {stats['qa_pairs']}")
        print(f"  • Обычные документы: {stats['regular_docs']}")
        print(f"\nСсылки на документы:")
        print(f"  • Со ссылками: {stats['with_links']}")
        print(f"  • Без ссылок: {stats['without_links']}")
        print(f"\nДополнительно:")
        print(f"  • Обрезано документов: {stats['truncated']}")
        print(f"  • Пропущено (дубликаты): {stats['skipped']}")
        print(f"\nРазмер выходного файла: {self.output_path.stat().st_size / 1024:.2f} KB")
        print(f"Количество записей: {len(result)}")
        print("=" * 70)

        return result

    def print_sample(self, num_samples: int = 3):
        """Выводит примеры из сконвертированного файла"""
        if not self.output_path.exists():
            print("Файл не найден. Сначала запустите convert()")
            return

        with open(self.output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print("\n" + "=" * 70)
        print(f"📝 ПРИМЕРЫ ЗАПИСЕЙ (первые {num_samples})")
        print("=" * 70)

        for i, (key, value) in enumerate(list(data.items())[:num_samples], 1):
            print(f"\n{i}. Ключ: {key}")
            print(f"   Ссылка: {value['doc_link'] if value['doc_link'] else 'Нет ссылки'}")
            text_preview = value['text'][:200] + "..." if len(value['text']) > 200 else value['text']
            print(f"   Текст: {text_preview}")
            print(f"   Длина текста: {len(value['text'])} символов")

    def export_to_markdown(self, markdown_path: str = None):
        """Экспортирует данные в Markdown формат с ссылками"""
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

                # Добавляем ссылку, если есть
                if value['doc_link']:
                    f.write(f"**Источник:** [{value['doc_link']}]({value['doc_link']})\n\n")
                else:
                    f.write(f"**Источник:** Нет ссылки\n\n")

                f.write(f"{value['text']}\n\n")
                f.write(f"*Длина текста: {len(value['text'])} символов*\n\n")
                f.write("---\n\n")

        print(f"\n✅ Экспортировано в Markdown: {markdown_path}")

    def search_by_keyword(self, keyword: str) -> list:
        """Поиск записей по ключевому слову"""
        if not self.output_path.exists():
            print("Файл не найден. Сначала запустите convert()")
            return []

        with open(self.output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        results = []
        keyword_lower = keyword.lower()

        for key, value in data.items():
            if keyword_lower in key.lower() or keyword_lower in value['text'].lower():
                results.append({
                    'key': key,
                    'doc_link': value['doc_link'],
                    'text_preview': value['text'][:200] + "..." if len(value['text']) > 200 else value['text']
                })

        return results


class FilteredEnhancedConverter(EnhancedQADataConverter):
    """Конвертер с возможностью фильтрации по типу документа"""

    def __init__(self, input_json_path: str, output_json_path: str = None,
                 max_length: int = 1000, include_types: list = None):
        """
        Args:
            include_types: список типов документов для включения ('qa', 'pdf', 'document' и т.д.)
        """
        super().__init__(input_json_path, output_json_path, max_length)
        self.include_types = include_types or ['qa', 'pdf', 'document']

    def convert_filtered(self) -> Dict[str, Dict[str, str]]:
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
            'with_links': 0,
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

            # Получаем ссылку
            doc_link = self.extract_doc_link(metadata)

            # Форматируем контент
            content = self.extract_document_content(document, metadata)
            content = self.clean_text(content)

            if len(content) > self.max_length:
                content = self.truncate_text(content)
                stats['truncated'] += 1

            result[key] = {
                "text": content,
                "doc_link": doc_link
            }

            stats['included'] += 1
            if doc_link:
                stats['with_links'] += 1

            if stats['included'] % 10 == 0:
                print(f"   Обработано: {stats['included']} документов")

        # Сохраняем результат
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 70)
        print("📊 СТАТИСТИКА (с фильтрацией)")
        print("=" * 70)
        print(f"Всего документов в исходном JSON: {stats['total']}")
        print(f"Отфильтровано (неподходящий тип): {stats['filtered_out']}")
        print(f"Включено в результат: {stats['included']}")
        print(f"  • Со ссылками: {stats['with_links']}")
        print(f"  • Без ссылок: {stats['included'] - stats['with_links']}")
        print(f"Из них обрезано до {self.max_length} символов: {stats['truncated']}")
        print("=" * 70)

        return result


def main():
    """Основная функция"""
    print("=" * 70)
    print("🔄 КОНВЕРТОР JSON В ФОРМАТ С ТЕКСТОМ И ССЫЛКАМИ")
    print("=" * 70)

    print("\nВыберите режим работы:")
    print("1. Стандартная конвертация (все документы)")
    print("2. Конвертация только QA пар")
    print("3. Конвертация только PDF документов")
    print("4. Конвертация с пользовательскими настройками")
    print("5. Поиск по ключевому слову в готовом файле")

    choice = input("\nВаш выбор (1-5): ").strip()

    INPUT_FILE = "chroma_data_with_qa.json"
    OUTPUT_FILE = "qa_format_with_links.json"
    MAX_LENGTH = 1000

    # Проверяем существование файла
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
        converter = EnhancedQADataConverter(INPUT_FILE, OUTPUT_FILE, MAX_LENGTH)
        result = converter.convert()
        converter.print_sample(3)

        # Предлагаем экспорт в Markdown
        export_md = input("\n📝 Экспортировать в Markdown? (y/N): ").strip().lower()
        if export_md == 'y':
            converter.export_to_markdown()

    elif choice == '2':
        # Только QA пары
        output_qa = "qa_pairs_with_links.json"
        converter = FilteredEnhancedConverter(INPUT_FILE, output_qa, MAX_LENGTH, include_types=['qa'])
        result = converter.convert_filtered()
        converter.print_sample(3)

    elif choice == '3':
        # Только PDF документы
        output_pdf = "pdf_documents_with_links.json"
        converter = FilteredEnhancedConverter(INPUT_FILE, output_pdf, MAX_LENGTH, include_types=['pdf', 'document'])
        result = converter.convert_filtered()
        converter.print_sample(3)

    elif choice == '4':
        # Пользовательские настройки
        print("\n🔧 Настройки конвертации:")

        custom_length = input(f"Максимальная длина текста (по умолчанию {MAX_LENGTH}): ").strip()
        if custom_length.isdigit():
            MAX_LENGTH = int(custom_length)

        custom_output = input(f"Имя выходного файла (по умолчанию {OUTPUT_FILE}): ").strip()
        if custom_output:
            OUTPUT_FILE = custom_output

        # Выбор типов для включения
        print("\nТипы документов для включения:")
        print("1. Все типы")
        print("2. Только QA пары")
        print("3. Только документы")
        print("4. QA пары и документы")

        type_choice = input("Выберите (1-4): ").strip()

        if type_choice == '1':
            converter = EnhancedQADataConverter(INPUT_FILE, OUTPUT_FILE, MAX_LENGTH)
        elif type_choice == '2':
            converter = FilteredEnhancedConverter(INPUT_FILE, OUTPUT_FILE, MAX_LENGTH, include_types=['qa'])
        elif type_choice == '3':
            converter = FilteredEnhancedConverter(INPUT_FILE, OUTPUT_FILE, MAX_LENGTH,
                                                  include_types=['pdf', 'document'])
        elif type_choice == '4':
            converter = FilteredEnhancedConverter(INPUT_FILE, OUTPUT_FILE, MAX_LENGTH,
                                                  include_types=['qa', 'pdf', 'document'])
        else:
            converter = EnhancedQADataConverter(INPUT_FILE, OUTPUT_FILE, MAX_LENGTH)

        result = converter.convert()
        converter.print_sample(5)

        # Предлагаем экспорт в Markdown
        export_md = input("\n📝 Экспортировать в Markdown? (y/N): ").strip().lower()
        if export_md == 'y':
            converter.export_to_markdown()

    elif choice == '5':
        # Поиск по ключевому слову
        if not Path(OUTPUT_FILE).exists():
            print(f"⚠️ Файл {OUTPUT_FILE} не найден. Сначала выполните конвертацию.")
            return

        converter = EnhancedQADataConverter(INPUT_FILE, OUTPUT_FILE, MAX_LENGTH)
        keyword = input("\n🔍 Введите ключевое слово для поиска: ").strip()

        if keyword:
            results = converter.search_by_keyword(keyword)
            print(f"\n📊 Найдено результатов: {len(results)}")
            for i, res in enumerate(results, 1):
                print(f"\n{i}. {res['key']}")
                print(f"   Ссылка: {res['doc_link'] if res['doc_link'] else 'Нет ссылки'}")
                print(f"   Текст: {res['text_preview']}")

    else:
        print("❌ Неверный выбор")
        return

    print("\n✅ Программа завершена!")


if __name__ == "__main__":
    main()