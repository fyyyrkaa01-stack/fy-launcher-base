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
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Находим ВООБЩЕ ВСЕ ссылки, ведущие на страницы плагинов (.html)
        all_links = soup.find_all('a', href=re.compile(r'/plugins/.*\.html'))
        print(f"Всего ссылок на плагины на странице: {len(all_links)}")
        
        added_links = set()
        idx = 0
        
        for link in all_links:
            href = link['href']
            # Приводим к полному URL
            if not href.startswith('http'):
                href = "https://vsthouse.ru" + href
                
            if href in added_links:
                continue
                
            # Ищем название плагина в тексте ссылки или у картинки внутри неё
            title = link.get_text(strip=True)
            img_elem = link.find('img')
            
            if img_elem and not title:
                title = img_elem.get('alt', '').strip()
                
            # Если ссылка — это просто кнопка "Подробнее" или пустая, ищем заголовок рядом
            parent = link.find_parent(['div', 'article', 'td', 'li'])
            if parent and (not title or len(title) < 5 or any(x in title.lower() for x in ["подробнее", "скачать", "коммент"])):
                # Пробуем найти заголовок внутри этого же блока
                h_elem = parent.find(['h2', 'h1', 'h3', 'h4', 'a'], class_=re.compile(r'.*'))
                if h_elem and h_elem != link:
                    title = h_elem.get_text(strip=True)
            
            # Проверки на валидность заголовка
            if not title or len(title) < 4 or any(x in title.lower() for x in ["комментарии", "подробнее", "категория", "читать", "скачать", "просмотров"]):
                continue
                
            # Ищем картинку в родительском блоке
            img_url = ""
            if parent:
                parent_img = parent.find('img')
                if parent_img:
                    img_url = parent_img.get('src', parent_img.get('data-src', ''))
            if not img_url and img_elem:
                img_url = img_elem.get('src', img_elem.get('data-src', ''))
                
            if img_url and not img_url.startswith('http'):
                img_url = "https://vsthouse.ru" + img_url
                
            # Текст описания
            desc = "Нажмите 'Открыть инфо' для просмотра деталей и скачивания торрента."
            if parent:
                # Ищем любой текстовый блок рядом
                for p_tag in parent.find_all(['p', 'div']):
                    p_text = p_tag.get_text(strip=True)
                    if len(p_text) > 20 and not p_tag.find('a') and p_tag != h_elem:
                        desc = p_text
                        break

            parsed_plugins.append({
                "id": f"vst_{idx}",
                "name": title[:30] + "..." if len(title) > 30 else title,
                "full_name": title,
                "version": "VST / VST3 / AAX",
                "link": href,
                "img_url": img_url,
                "desc": desc[:197] + "..." if len(desc) > 200 else desc
            })
            added_links.add(href)
            idx += 1

        print(f"Итого собрано валидных плагинов для записи: {len(parsed_plugins)}")

        # Сохраняем базу (если пусто — сохраняем тестовый плагин, чтобы лаунчер не падал)
        if not parsed_plugins:
            print("Парсер собрал 0 плагинов. Записываем тестовую базу, чтобы проверить связь.")
            parsed_plugins = [{
                "id": "vst_test",
                "name": "Serum (Тест связи)",
                "full_name": "Xfer Records - Serum v1.35b1 VST",
                "version": "VST / VST3 / AAX",
                "link": "https://vsthouse.ru/",
                "img_url": "https://vsthouse.ru/templates/vsthouse/images/logo.png",
                "desc": "База данных успешно подключена к лаунчеру! Если вы видите эту карточку, значит лаунчер работает с GitHub правильно."
            }]

        with open("plugins.json", "w", encoding="utf-8") as f:
            json.dump(parsed_plugins, f, ensure_ascii=False, indent=4)
        print(f"Успешно записано в plugins.json.")

    except Exception as e:
        print(f"Произошла ошибка при парсинге: {e}")

if __name__ == "__main__":
    parse_plugins()
