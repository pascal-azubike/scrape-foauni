import json
from collections import defaultdict

def ensure_category_list(value):
    """Convert a category value to a list if it's not None"""
    if value is None:
        return []
    return [value] if not isinstance(value, list) else value

def deduplicate_products(input_file='products.json', output_file='products_dedup.json'):
    # Load the JSON data
    with open(input_file, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    print(f"Original number of products: {len(products)}")
    
    # Use defaultdict to collect all products by SKU
    products_by_sku = defaultdict(list)
    
    # Group products by SKU
    for product in products:
        sku = product.get('sku')
        if sku:
            products_by_sku[sku].append(product)
    
    # Process each group of products with the same SKU
    deduplicated_products = []
    
    for sku, product_group in products_by_sku.items():
        if len(product_group) > 1:
            # Product appears in multiple categories - merge them
            base_product = product_group[0].copy()
            
            # Initialize category sets to track unique categories
            main_categories = set()
            sub_categories = set()
            product_types = set()
            
            # Collect all unique categories
            for product in product_group:
                if product.get('main_category'):
                    main_categories.add(product['main_category'])
                if product.get('sub_category'):
                    sub_categories.add(product['sub_category'])
                if product.get('product_type'):
                    product_types.add(product['product_type'])
            
            # Convert sets to sorted lists and update the base product
            base_product['main_category'] = sorted(list(main_categories)) if main_categories else []
            base_product['sub_category'] = sorted(list(sub_categories)) if sub_categories else []
            base_product['product_type'] = sorted(list(product_types)) if product_types else []
            
            print(f"Merged categories for SKU {sku}:")
            print(f"Title: {base_product['title']}")
            print(f"Main categories: {base_product['main_category']}")
            print(f"Sub categories: {base_product['sub_category']}")
            print(f"Product types: {base_product['product_type']}")
            print("-" * 80)
            
            deduplicated_products.append(base_product)
        else:
            # Product appears only once - convert its categories to lists
            product = product_group[0].copy()
            product['main_category'] = ensure_category_list(product.get('main_category'))
            product['sub_category'] = ensure_category_list(product.get('sub_category'))
            product['product_type'] = ensure_category_list(product.get('product_type'))
            deduplicated_products.append(product)
    
    print(f"Number of products after deduplication: {len(deduplicated_products)}")
    
    # Write the deduplicated data back to a new file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(deduplicated_products, f, ensure_ascii=False, indent=4)
    
    print(f"Deduplicated data written to {output_file}")

if __name__ == "__main__":
    deduplicate_products() 