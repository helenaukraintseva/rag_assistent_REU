import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


def get_pdf_links(url):
    """
    Получает все ссылки на PDF-файлы с указанной веб-страницы.
    """
    # ✅ Рекомендация 1: Подмена User-Agent, чтобы сайт думал, что это браузер
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # Выполняем GET-запрос
        response = requests.get(url, headers=headers, timeout=10)  # , verify=False
        response.raise_for_status()  # выбросит исключение при плохом статусе (4xx, 5xx)

        # Парсим HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Находим все теги <a> с атрибутом href
        all_links = soup.find_all('a', href=True)

        # Список для хранения ссылок на PDF
        pdf_links = []

        for link in all_links:
            href = link['href']
            # Проверяем, что ссылка указывает на PDF (регистр букв не важен)
            if href.lower().endswith('.pdf'):
                # Преобразуем относительную ссылку в абсолютную
                full_url = urljoin(url, href)
                pdf_links.append(full_url)

        return pdf_links

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к сайту: {e}")
        return []


# Пример использования
if __name__ == "__main__":
    target_url = "https://rea.ru/Sveden/document"  # Ваша ссылка

    print(f"Ищу PDF-файлы на странице: {target_url}")
    pdfs = get_pdf_links(target_url)

    if pdfs:
        print(f"\nНайдено {len(pdfs)} ссылок на PDF:\n")
        for idx, pdf_url in enumerate(pdfs, 1):
            print(f"{idx}. {pdf_url}")
    else:
        print("\nPDF-ссылок не найдено или сайт недоступен.")
