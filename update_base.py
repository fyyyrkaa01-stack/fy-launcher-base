import json
import cloudscraper
from bs4 import BeautifulSoup
import re
import urllib.parse
import requests

def parse_plugins():
    parsed_plugins = []
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    
    url = "https://vsthouse.ru/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8",
        "Referer": "https://vsthouse.ru/",
        "Connection": "keep-alive"
    }
    
    try:
        print(f"Запрос к сайту: {url}")
        response = scraper.get(url, headers=headers, timeout=15)
        html_content = response.text
        print(f"Статус ответа сайта: {response.status_code}")
        
        if response.status_code == 403 or "cloudflare" in html_content.lower() or "ddos-guard" in html_content.lower():
            print("Обнаружена блокировка (403/Cloudflare). Пробуем через прокси-api...")
            proxy_url = f"https://api.allorigins.win/get?url={urllib.parse.quote(url)}"
            api_res = requests.get(proxy_url, timeout=15)
            print(f"Статус ответа прокси: {api_res.status_code}")
            if api_res.status_code == 200:
                html_content = api_res.json().get('contents', '')
                
        soup = BeautifulSoup(html_content, 'html.parser')
        articles = soup.find_all(['div', 'article'], class_=re.compile(r'(short|post|item|product|story|entry)'))
        print(f"Найдено блоков с плагинами: {len(articles)}")
        
        if not articles:
            all_links = soup.find_all('a', href=re.compile(r'/plugins/.*\.html'))
            print(f"Альтернативный поиск: найдено ссылок на плагины: {len(all_links)}")
            articles = list(set([l.find_parent(['div', 'article']) for l in all_links if l.find_parent(['div', 'article'])]))
            print(f"После фильтрации родительских блоков: {len(articles)}")

        idx = 0
        added_links = set()

        for article in articles:
            if not article:
                continue
                
            title_link = article.find('a', href=re.compile(r'\.html$'))
            if not title_link and article.name == 'a':
                title_link = article

            if not title_link or not title_link.has_attr('href'):
                continue

            href = title_link['href']
            if href in added_links:
                continue

            title = title_link.get_text(strip=True)
            if not title:
                h_elem = article.find(['h2', 'h1', 'h3', 'div'], class_=re.compile(r'(title|name|header)'))
                if h_elem:
                    title = h_elem.get_text(strip=True)

            if not title or len(href) < 22 or any(x in title.lower() for x in ["комментарии", "подробнее", "категория", "читать", "скачать"]):
                continue

            img_elem = article.find('img')
            img_url = ""
            if img_elem:
                img_url = img_elem.get('src', img_elem.get('data-src', ''))

            if img_url and not img_url.startswith('http'):
                img_url = "https://vsthouse.ru" + img_url

            desc = "Нажмите 'Открыть инфо' для просмотра деталей и скачивания торрента."
            desc_elem = article.find(['div', 'p'], class_=re.compile(r'(text|story|desc|message|info|short|preview|eMessage)'))
            if desc_elem:
                desc_text = desc_elem.get_text(strip=True)
                if desc_text and len(desc_text) > 10:
                    desc = desc_text

            parsed_plugins.append({
                "id": f"vst_{idx}",
                "name": title[:30] + "..." if len(title) > 30 else title,
                "full_name": title,
                "version": "VST / VST3 / AAX",
                "link": href if href.startswith('http') else "https://vsthouse.ru" + href,
                "img_url": img_url,
                "desc": desc[:197] + "..." if len(desc) > 200 else desc
            })
            added_links.add(href)
            idx += 1

        print(f"Итого собрано валидных плагинов для записи: {len(parsed_plugins)}")

        # Сохраняем в файл ТОЛЬКО если что-то нашли, чтобы не затирать базу пустышкой
        if parsed_plugins:
            with open("plugins.json", "w", encoding="utf-8") as f:
                json.dump(parsed_plugins, f, ensure_ascii=False, indent=4)
            print(f"Успешно записано {len(parsed_plugins)} плагинов в plugins.json.")
        else:
            print("Список пуст. plugins.json не переписывался.")

    except Exception as e:
        print(f"Произошла ошибка при парсинге: {e}")

if __name__ == "__main__":
    parse_plugins()
