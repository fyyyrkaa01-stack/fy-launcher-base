import json
from bs4 import BeautifulSoup
import re
import requests
from curl_cffi import requests as curl_requests

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
    return list(set(proxies))

def make_request_via_proxy(url, proxy_list):
    for i, proxy in enumerate(proxy_list[:25]):
        try:
            proxy_dict = {
                "http": f"http://{proxy}",
                "https://vsthouse.ru/": f"http://{proxy}"
            }
            response = curl_requests.get(
                url, 
                impersonate="chrome120", 
                proxies=proxy_dict,
                timeout=10,
                headers={
                    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8",
                    "Referer": "https://vsthouse.ru/"
                }
            )
            if response.status_code == 200 and len(response.text) > 15000:
                return response.text
        except Exception:
            continue
    return ""

def parse_plugins():
    parsed_plugins = []
    proxy_list = get_free_proxies()
    print(f"Загружено {len(proxy_list)} потенциальных прокси для проверки.")
    
    added_links = set()
    idx = 0
    
    # Настраиваем количество страниц для сбора (собираем первые 5 страниц)
    pages_to_parse = 5
    
    for page in range(1, pages_to_parse + 1):
        if page == 1:
            current_url = "https://vsthouse.ru/"
        else:
            current_url = f"https://vsthouse.ru/page/{page}/"
            
        print(f"\n--- Парсим страницу {page} из {pages_to_parse}: {current_url} ---")
        html_content = make_request_via_proxy(current_url, proxy_list)
        
        if not html_content:
            print(f"Не удалось получить контент страницы {page}.")
            continue
            
        soup = BeautifulSoup(html_content, 'html.parser')
        all_links = soup.find_all('a', href=True)
        page_plugins_count = 0
        
        for link in all_links:
            href = link['href']
            
            if not ('/plugins/' in href or '/vst/' in href or href.endswith('.html')):
                continue
            if any(x in href for x in ['/loads/', '/reklama/', '/user/', '/rules/']):
                continue
            if not href.startswith('http'):
                href = "https://vsthouse.ru" + href
            if href in added_links or href in ["https://vsthouse.ru/plugins/", "https://vsthouse.ru/"]:
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
            added_links.add(href)
            idx += 1
            page_plugins_count += 1
            
        print(f"На странице {page} найдено новых плагинов: {page_plugins_count}")

    print(f"\n[Завершено] Итого успешно собрано плагинов в базу: {len(parsed_plugins)}")

    if not parsed_plugins:
        print("База пуста. Оставляем тест.")
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
    print("Запись в файл plugins.json выполнена.")

if __name__ == "__main__":
    parse_plugins()
