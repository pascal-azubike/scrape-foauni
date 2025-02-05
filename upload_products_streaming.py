from pymongo import MongoClient, UpdateOne, ASCENDING
import ijson
from typing import Set

# MongoDB connection settings
MONGO_URI = "mongodb+srv://pascalazubike100:yfiRzC02rO9HDwcl@cluster0.d62sy.mongodb.net/"
DB_NAME = "abc_lectronics"
COLLECTION_NAME = "products"

def ensure_indexes(collection):
    """Create or update indexes with proper error handling"""
    try:
        # Drop existing indexes except _id
        collection.drop_indexes()
        
        # Recreate all indexes
        collection.create_index("title")
        collection.create_index("sku", unique=True)
        collection.create_index("main_category")
        collection.create_index("sub_category")
        collection.create_index("product_type")
        collection.create_index("availability")
        collection.create_index("deleted")  # Add index for deleted field
        print("Indexes created successfully")
    except Exception as e:
        print(f"Error managing indexes: {str(e)}")

def upload_products_streaming(input_file='products_dedup.json'):
    try:
        # Connect to MongoDB
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        print("Connected to MongoDB successfully")

        # Get existing SKUs from database
        existing_skus: Set[str] = {doc['sku'] for doc in collection.find({}, {'sku': 1})}
        print(f"Found {len(existing_skus)} existing products in database")

        # Track metrics
        updates = 0
        inserts = 0
        marked_deleted = 0
        processed_skus: Set[str] = set()

        # Process JSON file in chunks
        batch_size = 1000
        update_batch = []
        insert_batch = []

        with open(input_file, 'rb') as file:
            # Create a parser for the JSON array
            parser = ijson.items(file, 'item')
            
            # Process each product
            for product in parser:
                sku = product.get('sku')
                if not sku:
                    continue

                processed_skus.add(sku)
                
                # Add deleted=false to all current products
                product['deleted'] = False
                
                if sku in existing_skus:
                    # Product exists - queue for update
                    update_batch.append(
                        UpdateOne(
                            {'sku': sku},
                            {'$set': product}
                        )
                    )
                else:
                    # New product - queue for insert
                    insert_batch.append(product)

                # Process update batch if it reaches batch size
                if len(update_batch) >= batch_size:
                    if update_batch:
                        collection.bulk_write(update_batch)
                        updates += len(update_batch)
                        print(f"Updated {updates} products so far")
                    update_batch = []

                # Process insert batch if it reaches batch size
                if len(insert_batch) >= batch_size:
                    if insert_batch:
                        collection.insert_many(insert_batch)
                        inserts += len(insert_batch)
                        print(f"Inserted {inserts} new products so far")
                    insert_batch = []

            # Process remaining batches
            if update_batch:
                collection.bulk_write(update_batch)
                updates += len(update_batch)
            
            if insert_batch:
                collection.insert_many(insert_batch)
                inserts += len(insert_batch)

            # Mark products as deleted if they're not in new data
            skus_to_mark_deleted = existing_skus - processed_skus
            if skus_to_mark_deleted:
                result = collection.update_many(
                    {'sku': {'$in': list(skus_to_mark_deleted)}},
                    {'$set': {'deleted': True}}
                )
                marked_deleted = result.modified_count
                print(f"Marked {marked_deleted} products as deleted")

        print(f"\nSync Complete:")
        print(f"Updated: {updates} products")
        print(f"Inserted: {inserts} new products")
        print(f"Marked as deleted: {marked_deleted} products")
        print(f"Total products in database: {collection.count_documents({})}")
        print(f"Active products: {collection.count_documents({'deleted': False})}")
        print(f"Deleted products: {collection.count_documents({'deleted': True})}")

        # Ensure indexes after all operations are complete
        ensure_indexes(collection)

        # Close connection
        client.close()
        print("MongoDB connection closed")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    upload_products_streaming() 

   