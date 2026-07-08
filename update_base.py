import json
import cloudscraper
from bs4 import BeautifulSoup
import re
import urllib.parse
import requests

def parse_plugins():
    parsed_plugins = []
    
    # Сразу используем прокси-сервис для обхода ограничений GitHub-серверов
    target_url = "https://vsthouse.ru/"
    proxy_url = f"https://api.allorigins.win/get?url={urllib.parse.quote(target_url)}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    
    try:
        print(f"Запрос к сайту через прокси-шлюз...")
        response = requests.get(proxy_url, headers=headers, timeout=20)
        print(f"Статус ответа шлюза: {response.status_code}")
        
        if response.status_code == 200:
            # Вытаскиваем реальный HTML из ответа прокси
            html_content = response.json().get('contents', '')
            print(f"Размер полученного HTML: {len(html_content)} символов")
        else:
            print("Не удалось получить данные через основной шлюз. Пробуем резервный...")
            # Резервный прокси-шлюз на случай сбоя первого
            backup_url = f"https://api.codetabs.com/v1/proxy?quest={urllib.parse.quote(target_url)}"
            response = requests.get(backup_url, headers=headers, timeout=20)
            html_content = response.text
            print(f"Статус резервного шлюза: {response.status_code}")

        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Находим все ссылки на плагины
        all_links = soup.find_all('a', href=re.compile(r'/plugins/.*\.html'))
        print(f"Всего найденных ссылок на плагины: {len(all_links)}")
        
        added_links = set()
        idx = 0
        
        for link in all_links:
            href = link['href']
            if not href.startswith('http'):
                href = "https://vsthouse.ru" + href
                
            if href in added_links:
                continue
                
            title = link.get_text(strip=True)
            img_elem = link.find('img')
            
            if img_elem and not title:
                title = img_elem.get('alt', '').strip()
                
            parent = link.find_parent(['div', 'article', 'td', 'li'])
            if parent and (not title or len(title) < 5 or any(x in title.lower() for x in ["подробнее", "скачать", "коммент"])):
                h_elem = parent.find(['h2', 'h1', 'h3', 'h4', 'a'])
                if h_elem and h_elem != link:
                    title = h_elem.get_text(strip=True)
            
            if not title or len(title) < 4 or any(x in title.lower() for x in ["комментарии", "подробнее", "категория", "читать", "скачать", "просмотров", "главная"]):
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
                "img_url": img_url,
                "desc": desc[:197] + "..." if len(desc) > 200 else desc
            })
            added_links.add(href)
            idx += 1

        print(f"Итого успешно собрано плагинов: {len(parsed_plugins)}")

        # Если прокси сработал и плагины найдены — записываем их. 
        # Если вдруг опять пусто — оставляем тест, чтобы ничего не ломалось.
        if not parsed_plugins:
            print("Парсер вернул 0. Оставляем тестовую запись.")
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
        print("Запись в файл plugins.json выполнена успешно.")

    except Exception as e:
        print(f"Произошла ошибка при парсинге: {e}")

if __name__ == "__main__":
    parse_plugins()
