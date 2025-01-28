import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
import json
import time
import re

class FouaniCategoryProducts:
    def __init__(self):
        self.base_url = "https://fouanistore.com/ng/en"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        self.session = requests.Session()
        self.products_dict = {}  # Dictionary to track unique products by SKU

    def normalize_url(self, url):
        """Normalize URL by ensuring single page parameter and consistent structure"""
        parsed = urlparse(url)
        query_dict = parse_qs(parsed.query)
        
        # Handle page parameter
        if 'page' in query_dict:
            # Take only the last page number if multiple exist
            last_page = query_dict['page'][-1]
            # Remove page parameter if it's 1, otherwise keep single value
            if last_page == '1':
                del query_dict['page']
            else:
                query_dict['page'] = [last_page]
        
        # Rebuild the URL with sorted parameters for consistency
        clean_query = urlencode(sorted(query_dict.items()), doseq=True)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if clean_query:
            normalized += f"?{clean_query}"
        return normalized

    def get_page_content(self, url):
        """Fetch page HTML content"""
        try:
            normalized_url = self.normalize_url(url)
            print(f"Fetching page: {normalized_url}")
            response = self.session.get(normalized_url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching page {normalized_url}: {str(e)}")
            return None

    def clean_text(self, text):
        """Clean and normalize text content"""
        if text:
            return ' '.join(text.strip().split())
        return None

    def extract_product_details(self, url, category_name):
        """Extract detailed information from a product page"""
        html_content = self.get_page_content(url)
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
            product_detail['title'] = self.clean_text(title_elem.text) if title_elem else None

            price_elem = soup.select_one('.price')
            if price_elem:
                price_text = self.clean_text(price_elem.text)
                price_value = re.sub(r'[^\d.]', '', price_text) if price_text else None
                product_detail['price'] = price_value

            # Extract availability from td element
            availability_elem = soup.select_one('td.availability')
            product_detail['availability'] = self.clean_text(availability_elem.text) if availability_elem else None

            sku_elem = detail_wrapper.select_one('.sku')
            product_detail['sku'] = self.clean_text(sku_elem.text) if sku_elem else None

            image_container = soup.select('.custom-dots img')
            product_detail['images'] = [
                urljoin(self.base_url, img['src'])
                for img in image_container
                if 'src' in img.attrs
            ]

            tags_images = soup.select('.tags-images img')
            product_detail['tags_images'] = [
                urljoin(self.base_url, img['src'])
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
                        key = self.clean_text(label.text)
                        val = self.clean_text(value.text)
                        if key and val:
                            specs[key] = val
                product_detail['specifications'] = specs

            return product_detail

        except Exception as e:
            print(f"Error extracting details from {url}: {str(e)}")
            return None

    def get_product_links(self, soup):
        """Extract product links from a category page"""
        product_links = []
        products_row = soup.select('.products-row')
        
        for row in products_row:
            product_items = row.select('a[href*="/product/"]')
            for item in product_items:
                if 'href' in item.attrs:
                    product_url = urljoin(self.base_url, item['href'])
                    product_links.append(self.normalize_url(product_url))
        
        return list(set(product_links))

    def get_pagination_urls(self, soup, base_category_url):
        """Extract and normalize pagination URLs from the category page"""
        pagination_urls = set()
        pagination = soup.select('.pagination a[href*="page="]')
        base_normalized = self.normalize_url(base_category_url)
        
        for page_link in pagination:
            if 'href' in page_link.attrs:
                page_url = urljoin(self.base_url, page_link['href'])
                normalized_url = self.normalize_url(page_url)
                if normalized_url != base_normalized:
                    pagination_urls.add(normalized_url)
        
        return sorted(list(pagination_urls))

    def process_category(self, category_url, category_name):
        """Process a category page and all its pagination pages"""
        processed_urls = set()
        next_page = category_url
        
        while next_page and self.normalize_url(next_page) not in processed_urls:
            normalized_url = self.normalize_url(next_page)
            print(f"\nProcessing category page: {normalized_url}")
            html_content = self.get_page_content(normalized_url)
            if not html_content:
                break
                
            soup = BeautifulSoup(html_content, 'html.parser')
            product_links = self.get_product_links(soup)
            print(f"Found {len(product_links)} products on this page")
            
            for product_url in product_links:
                print(f"Processing product: {product_url}")
                product_details = self.extract_product_details(product_url, category_name)
                
                if product_details and product_details['sku']:
                    sku = product_details['sku']
                    if sku in self.products_dict:
                        # Product exists, just add the category
                        if category_name not in self.products_dict[sku]['categories']:
                            self.products_dict[sku]['categories'].append(category_name)
                    else:
                        # New product
                        product_details['categories'] = [category_name]
                        self.products_dict[sku] = product_details
                
                time.sleep(2)
            
            processed_urls.add(normalized_url)
            pagination_urls = self.get_pagination_urls(soup, category_url)
            next_page = None
            
            for url in pagination_urls:
                if url not in processed_urls:
                    next_page = url
                    break
            
            time.sleep(2)

    def update_categories_with_products(self):
        """Update categories.json with normalized product information"""
        try:
            with open('categories.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                categories = data["categories"]
            
            # Process each category
            for i, category in enumerate(categories, 1):
                print(f"\nProcessing category {i}/{len(categories)}: {category['name']}")
                self.process_category(category['url'], category['name'])
                
            # Create the final normalized structure
            normalized_data = {
                "categories": [{"name": cat["name"], "url": self.normalize_url(cat["url"])} for cat in categories],
                "products": list(self.products_dict.values())
            }
            
            # Save the normalized data
            with open('normalized_products.json', 'w', encoding='utf-8') as f:
                json.dump(normalized_data, f, indent=2, ensure_ascii=False)
            
            print(f"\nProcessing complete. Total unique products: {len(self.products_dict)}")
            print("Data saved to normalized_products.json")
            
        except FileNotFoundError:
            print("Categories file not found. Please run the category finder first.")
        except Exception as e:
            print(f"Error updating categories with products: {str(e)}")

def main():
    processor = FouaniCategoryProducts()
    processor.update_categories_with_products()

if __name__ == "__main__":
    main()