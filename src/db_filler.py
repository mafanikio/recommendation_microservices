import csv
import os
from datetime import datetime
from random import randint

import pymongo
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.environ["MONGO_URI"]
DATASET_FILE_PATH = os.environ["DATASET_FILE_PATH"]

client = pymongo.MongoClient(MONGO_URI)
db = client.get_default_database()

users_collection = db["users"]
purchases_collection = db["purchases"]
items_collection = db["items"]

with open(DATASET_FILE_PATH) as f:
    csv_reader = csv.reader(f)
    header = next(csv_reader)

    for row in csv_reader:
        user_data = {
            "user_id": int(row[0]),
            "name": row[1],
            "age": int(row[2]),
            "gender": row[3],
            "location": row[4],
            "preferences": row[5],
        }

        # Check if user already exists
        if not users_collection.find_one({"user_id": user_data["user_id"]}):
            users_collection.insert_one(user_data)

        item_data = {
            "product_id": int(row[6]),
            "category": row[7],
            "product_name": row[8],
            "description": row[9],
            "tags": row[10] or "",
        }

        # Check if item already exists
        if not items_collection.find_one({"product_id": item_data["product_id"]}):
            items_collection.insert_one(item_data)

        purchase_data = {
            "purchase_id": randint(1000, 9999),  # Random purchase ID
            "product_id": item_data["product_id"],
            "user_id": user_data["user_id"],
            "quantity": randint(1, 4),
            "price": randint(10, 1000),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }

        purchases_collection.insert_one(purchase_data)

print(f"Imported {users_collection.count_documents({})} users")
print(f"Imported {items_collection.count_documents({})} items")
print(f"Imported {purchases_collection.count_documents({})} purchases")
