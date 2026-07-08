import json
import os
from bs4 import BeautifulSoup
import re
import requests
from curl_cffi import requests as curl_requests
import random

def get_free_proxies():
    print("Получаем свежий список прокси...")
    urls = [
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
    ]
    proxies = []
    for url in urls:
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                extracted = re.findall(r'\d+\.\d+\.\d+\.\d+:\d+', res.text)
                proxies.extend(extracted)
        except Exception:
            continue
    proxies = list(set(proxies))
    random.shuffle(proxies)
    return proxies

def parse_plugins():
    # 1. Загружаем уже существующую базу, чтобы не потерять старые плагины
    existing_plugins = []
    if os.path.exists("plugins.json"):
        try:
            with open("plugins.json", "r", encoding="utf-8") as f:
                existing_plugins = json.load(f)
                # Если там тестовая карточка, очищаем
                if len(existing_plugins) == 1 and existing_plugins[0].get("id") == "vst_test":
                    existing_plugins = []
            print(f"Загружено существующих плагинов из базы: {len(existing_plugins)}")
        except Exception:
            print("Не удалось прочитать plugins.json, создаем новую базу.")

    # Создаем пул существующих ссылок, чтобы не плодить дубликаты
    existing_links = {p["link"] for p in existing_plugins if "link" in p}

    parsed_plugins = []
    url = "https://vsthouse.ru/"
    proxy_list = get_free_proxies()
    
    html_content = ""
    success = False
    
    # Парсим ТОЛЬКО главную страницу (она стабильна)
    print("\n--- Стучимся на главную страницу vsthouse.ru ---")
    for i, proxy in enumerate(proxy_list[:30]):
        try:
            proxy_dict = {
                "http": f"http://{proxy}",
                "https://vsthouse.ru/": f"http://{proxy}"
            }
            response = curl_requests.get(
                url, 
                impersonate="chrome120", 
                proxies=proxy_dict,
                timeout=12,
                headers={
                    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8",
                    "Referer": "https://vsthouse.ru/"
                }
            )
            if response.status_code == 200 and len(response.text) > 15000:
                html_content = response.text
                print(f"Успех! Страница получена через прокси {proxy}")
                success = True
                break
        except Exception:
            continue

    if not success:
        print("Не удалось зайти через прокси. База не обновлена.")
        return

    soup = BeautifulSoup(html_content, 'html.parser')
    all_links = soup.find_all('a', href=True)
    
    new_count = 0
    # Начинаем индекс ID с конца существующей базы
    idx = len(existing_plugins)
    
    for link in all_links:
        href = link['href']
        
        if not ('/plugins/' in href or '/vst/' in href or href.endswith('.html')):
            continue
        if any(x in href for x in ['/loads/', '/reklama/', '/user/', '/rules/']):
            continue
        if not href.startswith('http'):
            href = "https://vsthouse.ru" + href
            
        # ПРОПУСКАЕМ, если этот плагин уже есть в нашей накопленной базе
        if href in existing_links or href in ["https://vsthouse.ru/plugins/", "https://vsthouse.ru/"]:
            continue
            
        title = link.get_text(strip=True)
        img_elem = link.find('img')
        
        if img_elem and not title:
            title = img_elem.get('alt', '').strip()
            
        parent = link.find_parent(['div', 'article', 'td', 'li', 'h2', 'h3'])
        if parent and (not title or len(title) < 5 or any(x in title.lower() for x in ["подробнее", "скачать", "коммент"])):
            h_elem = parent.find(['h2', 'h1', 'h3', 'h4', 'a'])
            if h_elem and h_elem != link:
                title = h_elem.get_text(strip=True)
        
        if not title or len(title) < 5 or any(x in title.lower() for x in ["комментарии", "подробнее", "категория", "читать", "скачать", "просмотров", "главная", "контакты"]):
            continue
            
        img_url = ""
        if parent:
            parent_img = parent.find('img')
            if parent_img:
                img_url = parent_img.get('src', parent_img.get('data-src', ''))
        if not img_url and img_elem:
            img_url = img_elem.get('src', img_elem.get('data-src', ''))
            
        if img_url and not img_url.startswith('http'):
            img_url = "https://vsthouse.ru" + img_url
            
        desc = "Нажмите 'Открыть инфо' для просмотра деталей и скачивания торрента."
        if parent:
            for p_tag in parent.find_all(['p', 'div']):
                p_text = p_tag.get_text(strip=True)
                if len(p_text) > 20 and not p_tag.find('a'):
                    desc = p_text
                    break

        parsed_plugins.append({
            "id": f"vst_{idx}",
            "name": title[:30] + "..." if len(title) > 30 else title,
            "full_name": title,
            "version": "VST / VST3 / AAX",
            "link": href,
            "img_url": img_url if img_url else "https://vsthouse.ru/templates/vsthouse/images/logo.png",
            "desc": desc[:197] + "..." if len(desc) > 200 else desc
        })
        existing_links.add(href)
        idx += 1
        new_count += 1

    # Соединяем старые плагины с только что найденными новинками
    final_base = existing_plugins + parsed_plugins
    print(f"Найдено свежих новинок: {new_count}. Итого в базе теперь: {len(final_base)}")

    with open("plugins.json", "w", encoding="utf-8") as f:
        json.dump(final_base, f, ensure_ascii=False, indent=4)
    print("Запись в файл plugins.json выполнена успешно.")

if __name__ == "__main__":
    parse_plugins()
