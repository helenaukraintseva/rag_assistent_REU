import time
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Настройка драйвера (убедитесь, что chromedriver установлен)
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # Убрать, если хотите видеть браузер
driver = webdriver.Chrome(options=options)

try:
    url = "https://rea.ru/"
    driver.get(url)

    # Ждем загрузки основной таблицы или контента (селектор НУЖНО УТОЧНИТЬ)
    # Пример: ждем появления расписания на день или неделю
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "schedule-table"))
    )

    # Даем еще секунду на подгрузку AJAX
    time.sleep(2)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # ----- РАЗДЕЛ 1: ПАРСИНГ ГРУПП / ПРЕПОДАВАТЕЛЕЙ (ВЫПАДАЮЩИЕ СПИСКИ) -----
    # Ищем селекты. Обычно у них id типа "group", "teacher" или class "select2"
    groups_select = driver.find_element(By.ID, "groupSelect")  # Пример ID
    groups_options = groups_select.find_elements(By.TAG_NAME, "option")

    groups_list = []
    for opt in groups_options:
        val = opt.get_attribute("value")
        text = opt.text
        if val and val != "0":
            groups_list.append({"id": val, "name": text})

    print(f"Найдено групп: {len(groups_list)}")

    # ----- РАЗДЕЛ 2: СБОР РАСПИСАНИЯ ДЛЯ КАЖДОЙ ГРУППЫ (ИТЕРАЦИЯ) -----
    all_schedule_data = []

    # Чтобы не нагружать сервер, возьмем только первые 2 группы для теста
    for group in groups_list[:2]:
        print(f"Парсинг группы: {group['name']}")

        # Выбираем группу из выпадающего списка
        select_element = driver.find_element(By.ID, "groupSelect")  # УТОЧНИТЬ ID
        select_element.click()
        # Ищем нужную опцию и кликаем
        option_xpath = f"//option[@value='{group['id']}']"
        driver.find_element(By.XPATH, option_xpath).click()

        # Ждем обновления таблицы
        time.sleep(2)

        # Нажимаем кнопку "Показать" (если она есть)
        # driver.find_element(By.ID, "showBtn").click()
        # time.sleep(1)

        # Парсим таблицу
        soup_group = BeautifulSoup(driver.page_source, 'html.parser')

        # ** ЗДЕСЬ НУЖНО ПОДСТАВИТЬ РЕАЛЬНЫЕ СЕЛЕКТОРЫ **
        # Например, строки таблицы могут быть с классом "pair"
        rows = soup_group.select(".schedule-table tbody tr")

        for row in rows:
            cells = row.find_all('td')
            if len(cells) > 3:
                schedule_item = {
                    "group": group['name'],
                    "time": cells[0].get_text(strip=True),
                    "subject": cells[1].get_text(strip=True),
                    "type": cells[2].get_text(strip=True),
                    "teacher": cells[3].get_text(strip=True),
                    "room": cells[4].get_text(strip=True) if len(cells) > 4 else ""
                }
                all_schedule_data.append(schedule_item)

    # ----- СОХРАНЕНИЕ РЕЗУЛЬТАТОВ -----
    if all_schedule_data:
        keys = all_schedule_data[0].keys()
        with open('rea_schedule.csv', 'w', newline='', encoding='utf-8-sig') as f:
            dict_writer = csv.DictWriter(f, keys)
            dict_writer.writeheader()
            dict_writer.writerows(all_schedule_data)
        print("Данные сохранены в rea_schedule.csv")
    else:
        print("Данные не найдены. Проверьте селекторы таблицы.")

except Exception as e:
    print(f"Ошибка: {e}")
    # Сохраним скриншот для отладки
    driver.save_screenshot("debug_screen.png")
    print("Сохранен скриншот debug_screen.png")

finally:
    driver.quit()