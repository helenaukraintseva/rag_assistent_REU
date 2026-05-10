import requests
from pathlib import Path


def download_pdf(url, output_filename=None):
    """
    Скачивает PDF-файл по указанной ссылке.

    Args:
        url (str): URL файла для скачивания.
        output_filename (str, optional): Имя для сохранения.
                                         Если None, берётся из URL.

    Returns:
        bool: True если скачивание успешно, False в противном случае.
    """
    try:
        # Выполняем GET-запрос с потоковой загрузкой
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()  # Проверяем, успешен ли запрос

        # Определяем имя файла
        if output_filename is None:
            output_filename = Path(url).name
            if not output_filename.endswith('.pdf'):
                output_filename = f"downloaded_file_{Path(url).stem}.pdf"

        # Сохраняем файл бинарно
        with open(output_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"✓ Успешно: {output_filename}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"✗ Ошибка при скачивании {url}: {e}")
        return False
    except Exception as e:
        print(f"✗ Непредвиденная ошибка при скачивании {url}: {e}")
        return False


def download_from_list(urls_list, download_folder="downloaded"):
    """
    Скачивает файлы из списка URL-адресов.

    Args:
        urls_list (list): Список URL-адресов для скачивания.
        download_folder (str, optional): Папка для сохранения файлов.
                                         Если None, сохраняет в текущую папку.

    Returns:
        tuple: (успешно_скачано, всего_ссылок)
    """
    # Создаём папку для скачиваний, если указана
    if download_folder:
        Path(download_folder).mkdir(parents=True, exist_ok=True)

    successful = 0
    total = len(urls_list)

    print(f"Начинаю скачивание {total} файлов...\n")

    for i, url in enumerate(urls_list, 1):
        print(f"[{i}/{total}] Обработка: {url}")

        # Определяем путь для сохранения
        if download_folder:
            filename = Path(url).name
            if not filename.endswith('.pdf'):
                filename = f"file_{i}.pdf"
            filepath = Path(download_folder) / filename
            success = download_pdf(url, filepath)
        else:
            success = download_pdf(url)

        if success:
            successful += 1
        print()  # Пустая строка для разделения

    return successful, total


# Список ссылок для скачивания
pdf_urls = [
    # Планы приема СПО по филиалам
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_plan_Bryansk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_plan_Erevan.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_plan_Ivanovo.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_plan_Krasnodar.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_plan_MPEK.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_plan_MPT.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_plan_MTKP.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_plan_Perm.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_plan_Sevastopol.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_plan_Smolensk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_plan_Tula.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_plan_Volgograd.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_plan_Voronezh.pdf",

    # Правила приема СПО и приложения
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema_pril_01.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema_pril_02.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema_pril_03.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema_pril_04.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema_pril_05.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema_pril_06.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema_pril_07.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema_pril_08.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema_pril_09.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema_pril_10_Bryansk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema_pril_11_Volgograd.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema_pril_12_Voronezh.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema_pril_13_Erevan.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema_pril_14_Ivanovo.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema_pril_15_Krasnodar.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema_pril_16_Perm.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema_pril_17_Smolensk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema_pril_18_Tula.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/02_spo_Pravila_priema_pril_19_Sevastopol.pdf",

    # Планы приема бакалавриат по филиалам
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_plan_Bryansk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_plan_Dubai.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_plan_Erevan.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_plan_Ivanovo.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_plan_Krasnodar.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_plan_Minsk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_plan_Mos.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_plan_Orenburg.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_plan_Perm.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_plan_Pyatigorsk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_plan_Sevastopol.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_plan_Smolensk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_plan_Tashkent.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_plan_Tula.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_plan_Ulan-Bator.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_plan_Volgograd.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_plan_Voronezh.pdf",

    # Правила приема бакалавриат и приложения
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_01.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_02.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_03.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_04.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_05.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_06.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_07.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_08.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_09.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_10.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_11.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_12.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_13_Bryansk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_14_Volgograd.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_15_Krasnodar.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_16_Orenburg.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_17_Perm.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_18_Smolensk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_19_Tashkent.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_20_Tula.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_21_Erevan.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_22_Voronezh.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_23_Dubai.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_24_Ivanovo.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_25_Minsk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_26_Pyatigorsk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_27_Sevastopol.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/03_bak_Pravila_priema_pril_28_Ulan-Bator.pdf",

    # Планы приема магистратура по филиалам
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_plan_Bryansk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_plan_Dubai.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_plan_Erevan.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_plan_Ivanovo.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_plan_Krasnodar.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_plan_Minsk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_plan_Mos.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_plan_Orenburg.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_plan_Perm.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_plan_Pyatigorsk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_plan_Sevastopol.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_plan_Smolensk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_plan_Tashkent.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_plan_Tula.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_plan_Volgograd.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_plan_Voronezh.pdf",

    # Правила приема магистратура и приложения
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_01.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_02.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_03.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_04.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_05.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_06.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_07.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_08.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_09_Pyatigorsk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_10_Sevastopol.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_11_Volgograd.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_12_Krasnodar.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_13_Orenburg.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_14_Perm.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_15_Smolensk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_16_Tula.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_17_Voronezh.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_18_Dubai.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_19_Ivanovo.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_20_Minsk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_21_Tashkent.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_22_Bryansk.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/04_mag_Pravila_priema_pril_23_Erevan.pdf",

    # Договоры об образовании
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Dogovor_asp1_fiz_lico.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Dogovor_asp2_ur_lico.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Dogovor_asp3_colekt_dogovor_bez_oplat.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Dogovor_asp4_colekt_dogovor_na_rebenka.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Dogovor_bak1_fiz_lico.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Dogovor_bak2_ur_lico.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Dogovor_bak3_colekt_dogovor.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Dogovor_bakmag7_fiz_eng.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Dogovor_bakmag8_ur_eng.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Dogovor_mag4_fiz_lico.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Dogovor_mag5_ur_lico.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Dogovor_mag6_colekt_dogovor.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Dogovor_SPO1_fiz_lico.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Dogovor_SPO2_ur_lico.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Dogovor_SPO3_colekt_dogovor.pdf",

    # Правила приема аспирантура
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Pravila_priema_asp.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Pravila_priema_asp_pril1_1.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Pravila_priema_asp_pril1_2.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Pravila_priema_asp_pril1_3.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Pravila_priema_asp_pril1_4.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Pravila_priema_asp_pril2.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Pravila_priema_asp_pril3.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Pravila_priema_asp_pril4.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Pravila_priema_asp_pril5.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Pravila_priema_asp_pril6.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Pravila_priema_asp_pril7.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Pravila_priema_asp_pril8_1.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Pravila_priema_asp_pril8_2.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Pravila_priema_asp_pril8_3.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Pravila_priema_asp_pril8_4.pdf",

    # Правила приема лицей
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Pravila_priema_Licei.pdf",

    # Положения о реализации программ
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/%D0%9F%D0%BE%D0%BB%D0%BE%D0%B6%D0%B5%D0%BD%D0%B8%D0%B5%20%D0%BE%20%D1%80%D0%B5%D0%B0%D0%BB%D0%B8%D0%B7%D0%B0%D1%86%D0%B8%D0%B8%20%D0%B4%D0%BE%D0%BF%D0%BE%D0%BB%D0%BD%D0%B8%D1%82%D0%B5%D0%BB%D1%8C%D0%BD%D1%8B%D1%85%20%D0%BE%D0%B1%D1%89%D0%B5%D0%BE%D0%B1%D1%80%D0%B0%D0%B7%D0%BE%D0%B2%D0%B0%D1%82%D0%B5%D0%BB%D1%8C%D0%BD%D1%8B%D1%85%20%D0%BF%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%BC.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/%D0%9F%D0%BE%D0%BB%D0%BE%D0%B6%D0%B5%D0%BD%D0%B8%D0%B5%20%D0%BE%20%D1%80%D0%B5%D0%B0%D0%BB%D0%B8%D0%B7%D0%B0%D1%86%D0%B8%D0%B8%20%D0%B4%D0%BE%D0%BF%D0%BE%D0%BB%D0%BD%D0%B8%D1%82%D0%B5%D0%BB%D1%8C%D0%BD%D1%8B%D1%85%20%D0%BF%D1%80%D0%BE%D1%84%D0%B5%D1%81%D1%81%D0%B8%D0%BE%D0%BD%D0%B0%D0%BB%D1%8C%D0%BD%D1%8B%D1%85%20%D0%BF%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%BC.pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/%D0%9F%D0%BE%D0%BB%D0%BE%D0%B6%D0%B5%D0%BD%D0%B8%D0%B5%20%D0%BE%20%D1%80%D0%B5%D0%B0%D0%BB%D0%B8%D0%B7%D0%B0%D1%86%D0%B8%D0%B8%20%D0%BE%D1%81%D0%BD%D0%BE%D0%B2%D0%BD%D1%8B%D1%85%20%D0%BF%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%BC%20%D0%BF%D1%80%D0%BE%D1%84%D0%B5%D1%81%D1%81%D0%B8%D0%BE%D0%BD%D0%B0%D0%BB%D1%8C%D0%BD%D0%BE%D0%B3%D0%BE%20%D0%BE%D0%B1%D1%83%D1%87%D0%B5%D0%BD%D0%B8%D1%8F.pdf",

    # Правила приема дополнительное образование по филиалам
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/%D0%9F%D1%80%D0%B0%D0%B2%D0%B8%D0%BB%D0%B0%20%D0%BF%D1%80%D0%B8%D0%B5%D0%BC%D0%B0%20%D0%BD%D0%B0%20%D0%BE%D0%B1%D1%83%D1%87%D0%B5%D0%BD%D0%B8%D0%B5%20%D0%BF%D0%BE%20%D0%B4%D0%BE%D0%BF%D0%BE%D0%BB%D0%BD%D0%B8%D1%82%D0%B5%D0%BB%D1%8C%D0%BD%D1%8B%D0%BC%20%D0%BE%D0%B1%D1%80%D0%B0%D0%B7%D0%BE%D0%B2%D0%B0%D1%82%D0%B5%D0%BB%D1%8C%D0%BD%D1%8B%D0%BC%20%D0%BF%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%BC%D0%B0%D0%BC%20(%D0%9E%D1%80%D0%B5%D0%BD%D0%B1%D1%83%D1%80%D0%B3%D1%81%D0%BA%D0%B8%D0%B9%20%D1%84%D0%B8%D0%BB%D0%B8%D0%B0%D0%BB%20%D0%A0%D0%AD%D0%A3%20%D0%B8%D0%BC.%20%D0%93.%D0%92.%20%D0%9F%D0%BB%D0%B5%D1%85%D0%B0%D0%BD%D0%BE%D0%B2%D0%B0).pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/%D0%9F%D1%80%D0%B0%D0%B2%D0%B8%D0%BB%D0%B0%20%D0%BF%D1%80%D0%B8%D0%B5%D0%BC%D0%B0%20%D0%BD%D0%B0%20%D0%BE%D0%B1%D1%83%D1%87%D0%B5%D0%BD%D0%B8%D0%B5%20%D0%BF%D0%BE%20%D0%B4%D0%BE%D0%BF%D0%BE%D0%BB%D0%BD%D0%B8%D1%82%D0%B5%D0%BB%D1%8C%D0%BD%D1%8B%D0%BC%20%D0%BE%D0%B1%D1%89%D0%B5%D0%BE%D0%B1%D1%80%D0%B0%D0%B7%D0%BE%D0%B2%D0%B0%D1%82%D0%B5%D0%BB%D1%8C%D0%BD%D1%8B%D0%BC%20%D0%BF%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%BC%D0%B0%D0%BC%20(%D0%A1%D0%BC%D0%BE%D0%BB%D0%B5%D0%BD%D1%81%D0%BA%D0%B8%D0%B9%20%D1%84%D0%B8%D0%BB%D0%B8%D0%B0%D0%BB%20%D0%A0%D0%AD%D0%A3%20%D0%B8%D0%BC.%20%D0%93.%D0%92.%20%D0%9F%D0%BB%D0%B5%D1%85%D0%B0%D0%BD%D0%BE%D0%B2%D0%B0).pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/%D0%9F%D1%80%D0%B0%D0%B2%D0%B8%D0%BB%D0%B0%20%D0%BF%D1%80%D0%B8%D0%B5%D0%BC%D0%B0%20%D0%BD%D0%B0%20%D0%BE%D0%B1%D1%83%D1%87%D0%B5%D0%BD%D0%B8%D0%B5%20%D0%BF%D0%BE%20%D0%B4%D0%BE%D0%BF%D0%BE%D0%BB%D0%BD%D0%B8%D1%82%D0%B5%D0%BB%D1%8C%D0%BD%D1%8B%D0%BC%20%D0%BF%D1%80%D0%BE%D1%84%D0%B5%D1%81%D1%81%D0%B8%D0%BE%D0%BD%D0%B0%D0%BB%D1%8C%D0%BD%D1%8B%D0%BC%20%D0%BF%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%BC%D0%B0%D0%BC%20(%D0%A1%D0%BC%D0%BE%D0%BB%D0%B5%D0%BD%D1%81%D0%BA%D0%B8%D0%B9%20%D1%84%D0%B8%D0%BB%D0%B8%D0%B0%D0%BB%20%D0%A0%D0%AD%D0%A3%20%D0%B8%D0%BC.%20%D0%93.%D0%92.%20%D0%9F%D0%BB%D0%B5%D1%85%D0%B0%D0%BD%D0%BE%D0%B2%D0%B0).pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/%D0%9F%D1%80%D0%B0%D0%B2%D0%B8%D0%BB%D0%B0%20%D0%BF%D1%80%D0%B8%D0%B5%D0%BC%D0%B0%20%D0%BD%D0%B0%20%D0%BE%D0%B1%D1%83%D1%87%D0%B5%D0%BD%D0%B8%D0%B5%20%D0%BF%D0%BE%20%D0%BE%D1%81%D0%BD%D0%BE%D0%B2%D0%BD%D1%8B%D0%BC%20%D0%BF%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%BC%D0%B0%D0%BC%20%D0%B4%D0%BE%D0%BF%D0%BE%D0%BB%D0%BD%D0%B8%D1%82%D0%B5%D0%BB%D1%8C%D0%BD%D0%BE%D0%B3%D0%BE%20%D0%BE%D0%B1%D1%80%D0%B0%D0%B7%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D1%8F%20(%D0%92%D0%BE%D1%80%D0%BE%D0%BD%D0%B5%D0%B6%D1%81%D0%BA%D0%B8%D0%B9%20%D1%84%D0%B8%D0%BB%D0%B8%D0%B0%D0%BB%20%D0%A0%D0%AD%D0%A3%20%D0%B8%D0%BC.%20%D0%93.%D0%92.%20%D0%9F%D0%BB%D0%B5%D1%85%D0%B0%D0%BD%D0%BE%D0%B2%D0%B0).pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/%D0%9F%D1%80%D0%B0%D0%B2%D0%B8%D0%BB%D0%B0%20%D0%BF%D1%80%D0%B8%D0%B5%D0%BC%D0%B0%20%D0%BD%D0%B0%20%D0%BE%D0%B1%D1%83%D1%87%D0%B5%D0%BD%D0%B8%D0%B5%20%D0%BF%D0%BE%20%D0%BF%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%BC%D0%B0%D0%BC%20%D0%B4%D0%BE%D0%BF%D0%BE%D0%BB%D0%BD%D0%B8%D1%82%D0%B5%D0%BB%D1%8C%D0%BD%D0%BE%D0%B3%D0%BE%20%D0%BE%D0%B1%D1%80%D0%B0%D0%B7%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D1%8F%20(%D0%A1%D0%B5%D0%B2%D0%B0%D1%81%D1%82%D0%BE%D0%BF%D0%BE%D0%BB%D1%8C%D1%81%D0%BA%D0%B8%D0%B9%20%D1%84%D0%B8%D0%BB%D0%B8%D0%B0%D0%BB%20%D0%A0%D0%AD%D0%A3%20%D0%B8%D0%BC.%20%D0%93.%D0%92.%20%D0%9F%D0%BB%D0%B5%D1%85%D0%B0%D0%BD%D0%BE%D0%B2%D0%B0).pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/%D0%9F%D1%80%D0%B0%D0%B2%D0%B8%D0%BB%D0%B0%20%D0%BF%D1%80%D0%B8%D0%B5%D0%BC%D0%B0%20%D0%BD%D0%B0%20%D0%BE%D0%B1%D1%83%D1%87%D0%B5%D0%BD%D0%B8%D0%B5%20%D0%BF%D0%BE%20%D0%BF%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%BC%D0%B0%D0%BC%20%D0%BF%D1%80%D0%BE%D1%84%D0%B5%D1%81%D1%81%D0%B8%D0%BE%D0%BD%D0%B0%D0%BB%D1%8C%D0%BD%D0%BE%D0%B3%D0%BE%20%D0%BE%D0%B1%D1%83%D1%87%D0%B5%D0%BD%D0%B8%D1%8F%20(%D0%92%D0%BE%D1%80%D0%BE%D0%BD%D0%B5%D0%B6%D1%81%D0%BA%D0%B8%D0%B9%20%D1%84%D0%B8%D0%BB%D0%B8%D0%B0%D0%BB%20%D0%A0%D0%AD%D0%A3%20%D0%B8%D0%BC.%20%D0%93.%D0%92.%20%D0%9F%D0%BB%D0%B5%D1%85%D0%B0%D0%BD%D0%BE%D0%B2%D0%B0).pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/%D0%9F%D1%80%D0%B0%D0%B2%D0%B8%D0%BB%D0%B0%20%D0%BF%D1%80%D0%B8%D0%B5%D0%BC%D0%B0%20%D0%BD%D0%B0%20%D0%BE%D0%B1%D1%83%D1%87%D0%B5%D0%BD%D0%B8%D0%B5%20%D0%BF%D0%BE%20%D0%BF%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%BC%D0%B0%D0%BC%20%D0%BF%D1%80%D0%BE%D1%84%D0%B5%D1%81%D1%81%D0%B8%D0%BE%D0%BD%D0%B0%D0%BB%D1%8C%D0%BD%D0%BE%D0%B3%D0%BE%20%D0%BE%D0%B1%D1%83%D1%87%D0%B5%D0%BD%D0%B8%D1%8F%20(%D0%A1%D0%BC%D0%BE%D0%BB%D0%B5%D0%BD%D1%81%D0%BA%D0%B8%D0%B9%20%D1%84%D0%B8%D0%BB%D0%B8%D0%B0%D0%BB%20%D0%A0%D0%AD%D0%A3%20%D0%B8%D0%BC.%20%D0%93.%D0%92.%20%D0%9F%D0%BB%D0%B5%D1%85%D0%B0%D0%BD%D0%BE%D0%B2%D0%B0).pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/%D0%9F%D1%80%D0%B0%D0%B2%D0%B8%D0%BB%D0%B0%20%D0%BF%D1%80%D0%B8%D0%B5%D0%BC%D0%B0%20%D0%BD%D0%B0%20%D0%BF%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%BC%D1%8B%20%D0%B4%D0%BE%D0%BF%D0%BE%D0%BB%D0%BD%D0%B8%D1%82%D0%B5%D0%BB%D1%8C%D0%BD%D0%BE%D0%B3%D0%BE%20%D0%BF%D1%80%D0%BE%D1%84%D0%B5%D1%81%D1%81%D0%B8%D0%BE%D0%BD%D0%B0%D0%BB%D1%8C%D0%BD%D0%BE%D0%B3%D0%BE%20%D0%BE%D0%B1%D1%80%D0%B0%D0%B7%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D1%8F%20(%D0%9A%D1%80%D0%B0%D1%81%D0%BD%D0%BE%D0%B4%D0%B0%D1%80%D1%81%D0%BA%D0%B8%D0%B9%20%D1%84%D0%B8%D0%BB%D0%B8%D0%B0%D0%BB%20%D0%A0%D0%AD%D0%A3%20%D0%B8%D0%BC.%20%D0%93.%D0%92.%20%D0%9F%D0%BB%D0%B5%D1%85%D0%B0%D0%BD%D0%BE%D0%B2%D0%B0).pdf",
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/%D0%9F%D1%80%D0%B0%D0%B2%D0%B8%D0%BB%D0%B0%20%D0%BF%D1%80%D0%B8%D0%B5%D0%BC%D0%B0%20%D1%81%D0%BB%D1%83%D1%88%D0%B0%D1%82%D0%B5%D0%BB%D0%B5%D0%B9%20%D0%BD%D0%B0%20%D0%BE%D0%B1%D1%83%D1%87%D0%B5%D0%BD%D0%B8%D0%B5%20%D0%BF%D0%BE%20%D0%B4%D0%BE%D0%BF%D0%BE%D0%BB%D0%BD%D0%B8%D1%82%D0%B5%D0%BB%D1%8C%D0%BD%D1%8B%D0%BC%20%D0%BF%D1%80%D0%BE%D1%84%D0%B5%D1%81%D1%81%D0%B8%D0%BE%D0%BD%D0%B0%D0%BB%D1%8C%D0%BD%D1%8B%D0%BC%20%D0%BF%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%BC%D0%B0%D0%BC%20(%D0%91%D1%80%D1%8F%D0%BD%D1%81%D0%BA%D0%B8%D0%B9%20%D1%84%D0%B8%D0%BB%D0%B8%D0%B0%D0%BB%20%D0%A0%D0%AD%D0%A3%20%D0%B8%D0%BC.%20%D0%93.%D0%92.%20%D0%9F%D0%BB%D0%B5%D1%85%D0%B0%D0%BD%D0%BE%D0%B2%D0%B0).pdf",

    # Дополнительные документы
    "https://www.rea.ru/mnt/sveden/document/priemDocLink/Polozenie_egs_komiss.pdf",
]


# Пример использования 1: скачивание в текущую папку
success_count, total_count = download_from_list(pdf_urls)
print(f"\n{'=' * 50}")
print(f"Готово! Скачано {success_count} из {total_count} файлов.")

# Пример использования 2: скачивание в указанную папку
# success_count, total_count = download_from_list(pdf_urls, download_folder="my_pdfs")
# print(f"\nСкачано {success_count} из {total_count} файлов в папку 'my_pdfs'.")