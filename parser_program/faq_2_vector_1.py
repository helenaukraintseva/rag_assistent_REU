import json
from pathlib import Path


def append_qa_data_to_json(json_path, qa_dict, output_json_path=None):
    """
    Добавляет вопросы-ответы в существующий JSON файл

    Args:
        json_path: путь к существующему JSON файлу
        qa_dict: словарь с вопросами и ответами
        output_json_path: путь для сохранения обновленного JSON (если None, то перезаписывает исходный)
    """

    json_file = Path(json_path)

    # Проверяем существование файла
    if not json_file.exists():
        print(f"❌ JSON файл {json_path} не найден!")
        print(f"   Создаю новый файл с QA данными...")

        # Создаем новую структуру только с QA данными
        chroma_data = {
            "metadata": {
                "total_documents": len(qa_dict),
                "total_chars": sum(len(v) for v in qa_dict.values()),
                "type": "qa_database",
                "source": "manual_input"
            },
            "ids": [],
            "documents": [],
            "metadatas": []
        }

        # Добавляем QA данные
        for idx, (question, answer) in enumerate(qa_dict.items(), 1):
            doc_id = f"qa_{idx}_{question[:30].lower().replace(' ', '_').replace('?', '')}"
            doc_id = ''.join(c for c in doc_id if c.isalnum() or c == '_')

            chroma_data["ids"].append(doc_id)
            chroma_data["documents"].append(f"Вопрос: {question}\n\nОтвет: {answer}")
            chroma_data["metadatas"].append({
                "type": "qa",
                "question": question,
                "answer": answer,
                "question_length": len(question),
                "answer_length": len(answer),
                "index": idx
            })

        # Сохраняем в JSON
        output_path = Path(output_json_path) if output_json_path else json_path
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chroma_data, f, ensure_ascii=False, indent=2)

        print(f"✅ Создан новый JSON файл с {len(qa_dict)} QA парами: {output_path}")
        return chroma_data

    # Если файл существует, загружаем его
    print(f"📖 Загрузка существующего JSON файла: {json_path}")
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)

        print(f"✅ Загружено {len(existing_data.get('documents', []))} существующих документов")

        # Проверяем структуру
        if 'ids' not in existing_data:
            existing_data['ids'] = []
        if 'documents' not in existing_data:
            existing_data['documents'] = []
        if 'metadatas' not in existing_data:
            existing_data['metadatas'] = []
        if 'metadata' not in existing_data:
            existing_data['metadata'] = {}

        # Добавляем новые QA данные
        start_idx = len(existing_data['documents'])
        added_count = 0

        print(f"\n➕ Добавление новых QA пар...")
        for idx, (question, answer) in enumerate(qa_dict.items(), 1):
            # Проверяем, нет ли уже такого вопроса
            existing_questions = [m.get('question') for m in existing_data['metadatas'] if m.get('type') == 'qa']

            if question in existing_questions:
                print(f"   ⚠️ Вопрос уже существует, пропускаю: {question[:50]}...")
                continue

            # Создаем ID для QA пары
            doc_id = f"qa_{start_idx + added_count + 1}_{question[:30].lower().replace(' ', '_').replace('?', '')}"
            doc_id = ''.join(c for c in doc_id if c.isalnum() or c == '_')

            # Добавляем в массивы
            existing_data['ids'].append(doc_id)
            existing_data['documents'].append(f"Вопрос: {question}\n\nОтвет: {answer}")
            existing_data['metadatas'].append({
                "type": "qa",
                "question": question,
                "answer": answer,
                "question_length": len(question),
                "answer_length": len(answer),
                "added_at": "new",
                "index": start_idx + added_count + 1
            })

            added_count += 1
            print(f"   ✅ Добавлен вопрос {added_count}: {question[:50]}...")

        # Обновляем метаданные
        existing_data['metadata']['total_documents'] = len(existing_data['documents'])
        existing_data['metadata']['total_chars'] = sum(len(d) for d in existing_data['documents'])
        existing_data['metadata']['qa_pairs_count'] = len(
            [m for m in existing_data['metadatas'] if m.get('type') == 'qa'])
        existing_data['metadata']['last_updated'] = "with_qa_data"

        # Сохраняем обновленный JSON
        output_path = Path(output_json_path) if output_json_path else json_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)

        print(f"\n{'=' * 60}")
        print(f"✅ JSON файл успешно обновлен!")
        print(f"📊 Статистика обновления:")
        print(f"   - Добавлено новых QA пар: {added_count}")
        print(f"   - Всего документов в БД: {len(existing_data['documents'])}")
        print(f"   - Из них QA пар: {existing_data['metadata']['qa_pairs_count']}")
        print(f"   - Путь сохранения: {output_path}")
        print(f"{'=' * 60}")

        return existing_data

    except Exception as e:
        print(f"❌ Ошибка обработки JSON: {e}")
        return None


# Ваши данные
qa_data = {
    "Что делать если пропустил пары/зачёты/экзамены по болезни?": "Справка о временной нетрудоспособности должна быть оформлена по форме 095. Справку ОБЯЗАТЕЛЬНО заверить по почте санатория профилактория РЭУ им. Г.В. Плеханова medicine@rea.ru. После заверения оригинал справки необходимо принести в Единый Электронный Деканат (3 корпус 119 кабинет) в приемные часы. Если пропустили только пары — заявления писать не нужно, необходимо просто сдать справку для проставления уважительных неявок. Если пропустили зачеты/экзамены/пересдачи — необходимо будет написать заявление на продление сессии в Едином Электронном Деканате (3 корпус 119 кабинет).",

    "Приемные часы Единого Электронного Деканата (3 корпус, кабинеты: 111, 116, 117, 119, 121)": "Понедельник, среда, пятница — с 8:30 до 14:00. Вторник, четверг — с 13:30 до 19:00. Суббота — с 9:00 до 14:00.",

    "Как заказать справку для оформления налогового вычета?": "1. По оплатам налогоплательщика за 2023г: направить письмо (тема письма 'СПРАВКА за 2023г') на buh@rea.ru с указанием ФИО обучающегося, номера договора и запрашиваемого периода. 2. По оплатам налогоплательщика начиная с 2024г: дистанционно в ЛК студента (Главная → Заявки на получение справок → Справки → Тип запрашиваемого документа 'Справка об оплате (оплата производилась с 01.01.24г.)'). При отсутствии ЛК студента — заполнить ЗАЯВЛЕНИЕ (Excel) и СОГЛАСИЕ (скан с подписью) и направить на buh@rea.ru. Справка формируется в срок не позднее 30 календарных дней. С 01.04.2026г. в помещении кассы (этаж 3, кабинет №3.01 корпус 9): понедельник, пятница с 09:00 до 12:00; вторник, среда, четверг с 13:30 до 16:30.",

    "Где заказать справку об обучении?": "В личном кабинете студента в разделе «Справки». Справка готовится в течение 3 рабочих дней. Когда справка будет готова — в личном кабинете обновится статус «Подписано». После этого справку можно забирать в Едином Электронном Деканате (116 кабинет 3 корпуса) в приемные часы. Справка хранится в течение месяца после изготовления.",

    "Что делать если у меня возникли технические проблемы с ЛКС/moodle/антиплагиатом?": "Необходимо написать в чат тех.поддержки студентов в Telegram: https://t.me/+qzUFV-_lq9cwZjgy",

    "Что делать если долго не назначают пересдачу/академическую разницу?": "Обратиться в Единый Электронный Деканат (119 кабинет 3 корпуса) по вопросу назначения пересдачи/академической разницы.",

    "Что делать если меня нет в реестре студентов?": "Обратиться в Социальный отдел (343 кабинет 3 корпуса).",

    "Когда в расписании появятся пересдачи?": "Не позднее чем за 3 рабочих дня до дня пересдачи.",

    "Куда необходимо обращаться для оформления академического отпуска?": "Заявление на академический отпуск можно написать в Едином Электронном Деканате (119 кабинет 3 корпуса), также там можно проконсультироваться, какие документы необходимо предоставить.",

    "К кому обращаться если я хочу перевестись на другую Высшую школу?": "Обращаться в дирекцию Высшей школы, в которую хотите перевестись.",

    "Что делать если не пришла стипендия?": "Обычно стипендия приходит 25 числа каждого месяца. Если 25 число выпадает на выходной/праздник — в ближайший рабочий день до 25 числа. Если стипендия не пришла в течение недели после 25 числа — обратиться в Социальный отдел (343 кабинет 3 корпуса). Обычно если не приходит в первый месяц, то в следующем выплачивают за прошлый и текущий месяц.",

    "Где можно получить стипендиальную карту, если я ее не забрал ранее?": "Стипендиальные карты выдаются студентам 1 курса в течение сентября–октября в РЭУ на 1 этаже 3 корпуса. Если не успели забрать — подойти в ВТБ, который расположен возле главного входа в 3 корпус.",

    "Как зайти в личный кабинет студента, если ранее не регистрировался и не заходил в него?": "Зарегистрироваться в личный кабинет студента по номеру СНИЛСа, после чего указать адрес электронной почты, на который вышлют логин и пароль для входа в ЛКС.",

    "Какую справку необходимо приносить для допуска к прохождению практических занятий по дисциплинам «Физическая культура» и «Элективные дисциплины по физической культуре и спорту»?": "Справку по форме 086 у, полученную в поликлинике. В справке обязательно должна быть указана группа здоровья, справка заверена печатями поликлиники. Действительна 6 месяцев с момента получения. Если занятия проходят в разных залах — в каждый зал нужно принести по 1 копии справки."
}

if __name__ == "__main__":
    # Добавляем QA данные в существующий JSON или создаем новый
    updated_data = append_qa_data_to_json(
        json_path="chroma_data.json",  # путь к существующему JSON
        qa_dict=qa_data,
        output_json_path="chroma_data_with_qa.json"  # можно сохранить в новый файл
    )

    # Если нужно обновить исходный файл, используйте:
    # updated_data = append_qa_data_to_json("chroma_data.json", qa_data)

    if updated_data:
        print(f"\n💡 Пример добавленного документа:")
        # Показываем первый добавленный QA
        for i, metadata in enumerate(updated_data['metadatas']):
            if metadata.get('type') == 'qa' and metadata.get('added_at') == 'new':
                print(f"\nВопрос: {metadata['question']}")
                print(f"Ответ: {metadata['answer'][:150]}...")
                break