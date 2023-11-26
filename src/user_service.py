import json
import os

import redis
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from starlette.responses import StreamingResponse

load_dotenv()

app = FastAPI()

client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = client.get_default_database()

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")), db=int(os.getenv("REDIS_DB"))
)


class UserData(BaseModel):
    """Model for user data."""

    user_id: int
    name: str
    age: int
    gender: str
    location: str
    preferences: str


class PurchaseData(BaseModel):
    """Model for purchase data."""

    purchase_id: int
    product_id: int
    user_id: int
    quantity: int
    price: float
    timestamp: str


class ItemData(BaseModel):
    """Model for item data."""

    product_id: int
    category: str
    product_name: str
    description: str
    tags: str


async def _get_cached_data(key: str) -> dict:
    """Get cached data from Redis.

    Args:
        key (str): The key to retrieve data from Redis.

    Returns:
        dict: Cached data as a dictionary.
    """
    try:
        cached_data = await redis_client.get(key)
        if cached_data:
            return json.loads(cached_data)
    except redis.RedisError as e:
        logger.error(f"Redis error: {e}")
    return {}


async def _cache_data(key: str, data, expire_time=3600):
    """Cache data in Redis.

    Args:
        key (str): The key to store the data in Redis.
        data: The data to cache.
        expire_time (int, optional): Expiration time in seconds. Defaults to 3600.
    """
    try:
        await redis_client.setex(key, expire_time, json.dumps(data))
    except redis.RedisError as e:
        logger.error(f"Redis error: {e}")


# User endpoints
@app.post("/user/")
async def create_user(user_data: UserData):
    """Create a new user.

    Args:
        user_data (UserData): User data to create.

    Returns:
        dict: A message indicating the success of user creation.
    """
    await db.users.insert_one(user_data.dict())
    logger.info(f"Created user: {user_data.user_id}")
    return {"message": "User created successfully"}


@app.get("/user/{user_id}", response_model=UserData)
async def get_user(user_id: int):
    """Get user data by user ID.

    Args:
        user_id (int): The ID of the user to retrieve.

    Returns:
        UserData: User data.
    """
    cache_key = f"user:{user_id}"
    cached_data = await _get_cached_data(cache_key)
    if cached_data:
        logger.info(f"Cache hit for user_id: {user_id}")
        return cached_data

    user_data = await db.users.find_one({"user_id": user_id})
    if user_data:
        await _cache_data(cache_key, user_data)
        return UserData(**user_data)
    else:
        logger.error(f"User not found: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")


@app.delete("/user/{user_id}")
async def delete_user(user_id: int):
    """Delete a user by user ID.

    Args:
        user_id (int): The ID of the user to delete.

    Returns:
        dict: A message indicating the success of user deletion.
    """
    result = await db.users.delete_one({"user_id": user_id})
    if result.deleted_count:
        logger.info(f"Deleted user: {user_id}")
        return {"message": "User deleted successfully"}
    else:
        logger.error(f"User deletion failed: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")


# Purchase endpoints
@app.post("/purchase/")
async def create_purchase(purchase_data: PurchaseData):
    """Create a new purchase record.

    Args:
        purchase_data (PurchaseData): Purchase data to create.

    Returns:
        dict: A message indicating the success of purchase record creation.
    """
    await db.purchases.insert_one(purchase_data.dict())
    logger.info(f"Recorded purchase: {purchase_data.purchase_id}")
    return {"message": "Purchase recorded successfully"}


@app.get("/purchase/{purchase_id}", response_model=PurchaseData)
async def get_purchase(purchase_id: int):
    """Get purchase data by purchase ID.

    Args:
        purchase_id (int): The ID of the purchase to retrieve.

    Returns:
        PurchaseData: Purchase data.
    """
    cache_key = f"purchase:{purchase_id}"
    cached_data = await _get_cached_data(cache_key)
    if cached_data:
        logger.info(f"Cache hit for purchase_id: {purchase_id}")
        return cached_data

    purchase_data = await db.purchases.find_one({"purchase_id": purchase_id})
    if purchase_data:
        await _cache_data(cache_key, purchase_data)
        return PurchaseData(**purchase_data)
    else:
        logger.error(f"Purchase not found: {purchase_id}")
        raise HTTPException(status_code=404, detail="Purchase not found")


@app.put("/purchase/{purchase_id}")
async def update_purchase(purchase_id: int, purchase_data: PurchaseData):
    """Update a purchase record by purchase ID.

    Args:
        purchase_id (int): The ID of the purchase to update.
        purchase_data (PurchaseData): Updated purchase data.

    Returns:
        dict: A message indicating the success of purchase update.
    """
    result = await db.purchases.replace_one({"purchase_id": purchase_id}, purchase_data.dict())
    if result.modified_count:
        logger.info(f"Updated purchase: {purchase_id}")
        return {"message": "Purchase updated successfully"}
    else:
        logger.error(f"Purchase update failed: {purchase_id}")
        raise HTTPException(status_code=404, detail="Purchase not found")


@app.delete("/purchase/{purchase_id}")
async def delete_purchase(purchase_id: int):
    """Delete a purchase record by purchase ID.

    Args:
        purchase_id (int): The ID of the purchase to delete.

    Returns:
        dict: A message indicating the success of purchase deletion.
    """
    result = await db.purchases.delete_one({"purchase_id": purchase_id})
    if result.deleted_count:
        logger.info(f"Deleted purchase: {purchase_id}")
        return {"message": "Purchase deleted successfully"}
    else:
        logger.error(f"Purchase deletion failed: {purchase_id}")
        raise HTTPException(status_code=404, detail="Purchase not found")


@app.get("/interactions")
async def get_interactions():
    """Get user interactions as a CSV stream.

    Returns:
        StreamingResponse: A streaming response containing user interactions in CSV format.
    """
    pipeline = [
        {
            "$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "user_id",
                "as": "user_data",
            }
        },
        {"$unwind": "$user_data"},
        {
            "$lookup": {
                "from": "items",
                "localField": "product_id",
                "foreignField": "product_id",
                "as": "item_data",
            }
        },
        {"$unwind": "$item_data"},
        {
            "$project": {
                "_id": 0,
                "user_id": "$user_id",
                "name": "$user_data.name",
                "age": "$user_data.age",
                "gender": "$user_data.gender",
                "location": "$user_data.location",
                "preferences": "$user_data.preferences",
                "product_id": "$product_id",
                "category": "$item_data.category",
                "product_name": "$item_data.product_name",
                "description": "$item_data.description",
                "tags": "$item_data.tags",
            }
        },
    ]

    cursor = db.purchases.aggregate(pipeline)
    data = await cursor.to_list(length=None)

    def generate():
        yield "user_id;name;age;gender;location;preferences;product_id;category;product_name;description;tags\n"
        for item in data:
            yield ";".join(map(str, item.values())) + "\n"

    return StreamingResponse(generate(), media_type="text/csv")
