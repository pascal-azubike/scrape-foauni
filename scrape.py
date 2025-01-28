import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
import re
import time

# Base URL of the Fouani website
base_url = "https://fouanistore.com"

# Load the JSON data
with open('categories.json', 'r', encoding='utf-8') as f:
    categories = json.load(f)

# Function to get page content
def get_page_content(url):
    try:
        time.sleep(1)  # Add a 1-second delay between requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Error fetching page content from {url}: {e}")
        return None

# Function to clean text
def clean_text(text):
    return text.strip() if text else None

# Function to get product links from a category page
def get_product_links(url):
    html_content = get_page_content(url)
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the products-row div
    products_row = soup.select_one('.products-row')
    if not products_row:
        print("No products-row found on page")
        return []
    
    # Get all product links from the products-row
    product_links = []
    links = products_row.find_all('a')
    for link in links:
        if 'href' in link.attrs:
            full_url = urljoin(base_url, link['href'])
            print(f"Found product link: {full_url}")
            if full_url not in product_links:  # Avoid duplicates
                product_links.append(full_url)
    
    print(f"Found {len(product_links)} unique product links on page")
    return product_links

# Function to extract product details
def extract_product_details(url):
    print(f"Extracting details for: {url}")
    html_content = get_page_content(url)
    if not html_content:
        return None

    soup = BeautifulSoup(html_content, 'html.parser')
    product_detail = {}

    try:
        detail_wrapper = soup.select_one('.product-detail-wrapper')
        if not detail_wrapper:
            return None

        # Basic product information
        product_detail['url'] = url
        
        title_elem = detail_wrapper.select_one('.label')
        product_detail['title'] = clean_text(title_elem.text) if title_elem else None

        price_elem = soup.select_one('.price')
        if price_elem:
            price_text = clean_text(price_elem.text)
            price_value = re.sub(r'[^\d.]', '', price_text) if price_text else None
            product_detail['price'] = price_value

        # Extract availability from td element
        availability_elem = soup.select_one('td.availability')
        product_detail['availability'] = clean_text(availability_elem.text) if availability_elem else None

        sku_elem = detail_wrapper.select_one('.sku')
        product_detail['sku'] = clean_text(sku_elem.text) if sku_elem else None

        image_container = soup.select('.custom-dots img')
        product_detail['images'] = [
            urljoin(base_url, img['src'])
            for img in image_container
            if 'src' in img.attrs
        ]

        tags_images = soup.select('.tags-images img')
        product_detail['tags_images'] = [
            urljoin(base_url, img['src'])
            for img in tags_images
            if 'src' in img.attrs
        ]

        description_panel = soup.select('.panel.active')[0] if soup.select('.panel.active') else None
        if description_panel:
            description_text = description_panel.select_one('.texts')
            if description_text:
                description_lines = [line.strip() for line in description_text.get_text(separator='\n').split('\n') if line.strip()]
                product_detail['description'] = '\n'.join(description_lines)

        specs_panel = soup.select('.panel.active')[1] if len(soup.select('.panel.active')) > 1 else None
        if specs_panel:
            specs = {}
            spec_rows = specs_panel.select('tr')
            for row in spec_rows:
                label = row.select_one('.row-label')
                value = row.select_one('.row-value')
                if label and value:
                    key = clean_text(label.text)
                    val = clean_text(value.text)
                    if key and val:
                        specs[key] = val
            product_detail['specifications'] = specs

        print(f"Successfully extracted details for: {product_detail.get('title', 'Unknown Product')}")
        return product_detail

    except Exception as e:
        print(f"Error extracting details from {url}: {str(e)}")
        return None

# Function to extract all products from a category, including pagination
def extract_all_products_from_category(category_url, category_hierarchy):
    """
    Extract all products from a category, including pagination
    category_hierarchy is a list containing [category1, category2, category3]
    """
    all_products = []
    page_number = 1
    
    while True:
        # Construct the URL for the current page
        parsed_url = urlparse(category_url)
        query_params = parse_qs(parsed_url.query)
        query_params['page'] = [str(page_number)]
        new_query = urlencode(query_params, doseq=True)
        page_url = parsed_url._replace(query=new_query).geturl()
        
        print(f"\nVisiting category page: {page_url}")
        
        # Get all product links from the current page
        product_links = get_product_links(page_url)
        
        if not product_links:
            print("No product links found on this page, moving to next category")
            break
        
        # Extract details for each product
        for product_url in product_links:
            product_details = extract_product_details(product_url)
            if product_details:
                # Add category hierarchy to product details
                product_details['main_category'] = category_hierarchy[0] if len(category_hierarchy) > 0 else None
                product_details['sub_category'] = category_hierarchy[1] if len(category_hierarchy) > 1 else None
                product_details['product_type'] = category_hierarchy[2] if len(category_hierarchy) > 2 else None
                all_products.append(product_details)
                print(f"Added product: {product_details.get('title', 'Unknown')}")
        
        # Check for next page
        html_content = get_page_content(page_url)
        if html_content:
            soup = BeautifulSoup(html_content, 'html.parser')
            # Look for the next page link
            next_page = soup.select_one(f'.pagination-link-label[href*="page={page_number + 1}"]')
            if not next_page:
                print("No more pages found")
                break
        
        page_number += 1
    
    return all_products

def save_products_to_json(products, filename='products.json'):
    """
    Append new products to existing JSON file or create new file if it doesn't exist
    """
    try:
        # Try to read existing products
        existing_products = []
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                existing_products = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # File doesn't exist or is empty/invalid
            pass
        
        # Append new products
        all_products = existing_products + products
        
        # Write back to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_products, f, ensure_ascii=False, indent=4)
            
        print(f"Successfully saved {len(products)} new products. Total products: {len(all_products)}")
        
    except Exception as e:
        print(f"Error saving products to JSON: {e}")

# Function to recursively visit each link in the JSON structure
def visit_links(categories, category_hierarchy=[]):
    """
    Recursively visit links while maintaining category hierarchy
    """
    all_products = []
    for category in categories:
        current_hierarchy = category_hierarchy.copy()
        current_hierarchy.append(category.get('title', 'Unknown Category'))
        
        if 'submenu' in category:
            # Recursively process submenu
            print(f"\nProcessing submenu for: {category.get('title', 'Unknown Category')}")
            submenu_products = visit_links(category['submenu'], current_hierarchy)
            all_products.extend(submenu_products)
        elif 'link' in category:
            # Process category page
            print(f"\nProcessing category: {category.get('title', 'Unknown Category')}")
            print(f"Category hierarchy: {' > '.join(current_hierarchy)}")
            full_url = urljoin(base_url, category['link'])
            category_products = extract_all_products_from_category(full_url, current_hierarchy)
            
            # Save products from this category
            if category_products:
                save_products_to_json(category_products)
                all_products.extend(category_products)
            
            print(f"Processed category: {category.get('title', 'Unknown Category')}")
            print(f"Products in this category: {len(category_products)}")

    return all_products

# Start visiting links
all_products = visit_links(categories)
print(f"Total products scraped: {len(all_products)}")