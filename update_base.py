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
    # 1. Загружаем существующие базы из synths.json и effects.json, чтобы ничего не потерять
    existing_synths = []
    existing_effects = []
    
    if os.path.exists("synths.json"):
        try:
            with open("synths.json", "r", encoding="utf-8") as f:
                existing_synths = json.load(f)
        except Exception:
            print("Не удалось прочитать synths.json, создаем пустой список.")

    if os.path.exists("effects.json"):
        try:
            with open("effects.json", "r", encoding="utf-8") as f:
                existing_effects = json.load(f)
        except Exception:
            print("Не удалось прочитать effects.json, создаем пустой список.")

    # Объединяем старые пулы ссылок, чтобы не плодить дубликаты
    existing_links = set()
    for p in existing_synths + existing_effects:
        if "link" in p:
            existing_links.add(p["link"])

    print(f"Загружено из старой базы: {len(existing_synths)} синтов и {len(existing_effects)} эффектов.")

    new_synths = []
    new_effects = []
    
    url = "https://vsthouse.ru/"
    proxy_list = get_free_proxies()
    
    html_content = ""
    success = False
    
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
    
    # Считаем общий индекс для генерации ID новых карточек
    total_existing_count = len(existing_synths) + len(existing_effects)
    idx = total_existing_count
    
    for link in all_links:
        href = link['href']
        
        if not ('/plugins/' in href or '/vst/' in href or '/load/' in href or href.endswith('.html')):
            continue
        if any(x in href for x in ['/loads/', '/reklama/', '/user/', '/rules/']):
            continue
        if not href.startswith('http'):
            href = "https://vsthouse.ru" + href
            
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

        plugin_data = {
            "id": f"vst_{idx}",
            "name": title[:30] + "..." if len(title) > 30 else title,
            "full_name": title,
            "version": "VST / VST3 / AAX",
            "link": href,
            "img_url": img_url if img_url else "https://vsthouse.ru/templates/vsthouse/images/logo.png",
            "desc": desc[:197] + "..." if len(desc) > 200 else desc
        }

        # СОРТИРОВКА: определяем, синт это или эффект по элементам ссылки
        href_lower = href.lower()
        if "sintezatory" in href_lower or "romlery" in href_lower or "synths" in href_lower or "vst_instrumenty" in href_lower:
            new_synths.append(plugin_data)
        else:
            # Все остальное (эквалайзеры, реверы, дилеи, сатураторы) распределяем в эффекты
            new_effects.append(plugin_data)

        existing_links.add(href)
        idx += 1

    # ВАЖНО: Новые плагины соединяем ТАК, чтобы новинки были в самом начале списка (сверху страницы)
    final_synths = new_synths + existing_synths
    final_effects = new_effects + existing_effects
    final_search = final_synths + final_effects

    print(f"\n--- Итоги парсинга ---")
    print(f"Добавлено новых синтов: {len(new_synths)} (Всего стало: {len(final_synths)})")
    print(f"Добавлено новых эффектов: {len(new_effects)} (Всего стало: {len(final_effects)})")

    # Перезаписываем обновленные файлы структуры
    with open("synths.json", "w", encoding="utf-8") as f:
        json.dump(final_synths, f, ensure_ascii=False, indent=4)

    with open("effects.json", "w", encoding="utf-8") as f:
        json.dump(final_effects, f, ensure_ascii=False, indent=4)

    with open("all_search.json", "w", encoding="utf-8") as f:
        json.dump(final_search, f, ensure_ascii=False, indent=4)

    print("Все три файла (synths.json, effects.json, all_search.json) успешно обновлены!")

if __name__ == "__main__":
    parse_plugins()
