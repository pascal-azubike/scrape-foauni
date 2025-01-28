from bs4 import BeautifulSoup
import requests
import json

def parse_menu(url):
    response = requests.get(url)
    html_content = response.content

    soup = BeautifulSoup(html_content, 'html.parser')

    def clean_title(title):
        if not title:
            return ''
        title = str(title)
        title = ' '.join(title.split())
        if 'i class' in title.lower():
            title = title.split('i class')[0]
        soup_title = BeautifulSoup(title, 'html.parser')
        return soup_title.get_text().strip()

    def extract_menu_item(item, depth=0, seen_titles=set()):
        if not item:
            return None

        link = item.find('a', recursive=True)
        if not link:
            return None

        title = ''
        title_sources = [
            link.get('data-title', ''),
            link.get('title', ''),
            link.string,
            link.get_text()
        ]

        for source in title_sources:
            if source:
                title = clean_title(source)
                if title:
                    break

        if not title:
            title = clean_title(item.get_text())

        if not title or title in seen_titles:
            return None

        # Mark the title as seen at the current depth
        seen_titles.add(title)

        result = {
            "title": title,
            "link": link.get('href', '')
        }

        submenu_items = []

        enclosures = item.find_all('div', class_='encloureClass enclosed', recursive=True)

        if enclosures:
            for enclosure in enclosures:
                sub_items = enclosure.find_all('li', class_='item', recursive=False)
                for sub_item in sub_items:
                    sub_menu_item = extract_menu_item(sub_item, depth + 1, seen_titles)
                    if sub_menu_item:
                        submenu_items.append(sub_menu_item)
        else:
            if depth < 2:  # Only include sub-items within level-1 or level-2
                submenus = item.find_all('ul', class_='main-menu level-m level-{}'.format(depth + 2), recursive=False)
                for submenu in submenus:
                    sub_items = submenu.find_all('li', class_='item')
                    for sub_item in sub_items:
                        sub_menu_item = extract_menu_item(sub_item, depth + 1, seen_titles)
                        if sub_menu_item:
                            submenu_items.append(sub_menu_item)

        if submenu_items:
            result["submenu"] = submenu_items

        return result

    main_menu = []
    menu_containers = soup.find_all('ul', class_='main-menu level-1')


    global executed_once
    executed_once = False  # Flag to track if the loop has executed once

    for container in menu_containers:
        if not executed_once:
            print("i have run ,.....................................................")
            top_items = container.find_all('li', class_='item', recursive=False)
            for item in top_items:
                seen_titles = set()  # Reset seen titles for each top-level menu item
                menu_item = extract_menu_item(item, 0, seen_titles)
                if menu_item:
                    main_menu.append(menu_item)
            executed_once = True  # Set the flag to True after the loop has executed once
        else:
            break  # Exit the loop if the flag is already True
    return {"main_menu": main_menu}

def save_menu_to_json(menu_data, filename='menu_structure.json'):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(menu_data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    menu_structure = parse_menu('https://fouanistore.com/public/ng/en')
    save_menu_to_json(menu_structure)
    print(json.dumps(menu_structure, indent=2, ensure_ascii=False))
