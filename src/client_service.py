import json
import os

import httpx
import redis
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from loguru import logger
from pydantic import BaseModel

load_dotenv()

API_KEY_NAME = "X-API-KEY"
API_KEY = os.getenv("API_KEY")

app = FastAPI()
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")), db=int(os.getenv("REDIS_DB"))
)
RECOMMENDATION_SERVICE_URL = os.getenv("RECOMMENDATION_SERVICE_URL")

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


class RecommendationResponse(BaseModel):
    user_id: int
    recommendations: list[dict[str, str | int]]


async def get_api_key(
    api_key: str = Security(APIKeyHeader(name=API_KEY_NAME, auto_error=False))
) -> str:
    """
    Validate API key

    Params:
        api_key: API key from client

    Returns:
        api_key: Validated API key
    """
    if api_key == API_KEY:
        return api_key
    else:
        raise HTTPException(status_code=403, detail="Invalid API Key")


@app.get("/recommendations/{user_id}")
async def get_recommendations(
    user_id: int, num_recommendations: int = 5,  # _api_key: str = Depends(get_api_key)
) -> RecommendationResponse:
    """
    Get cached recommendations for a user if exists, otherwise fetch from
    recommendation service

    Params:
        user_id: ID of user to fetch recommendations for
        num_recommendations: Number of recommendations to fetch

    Returns:
        List of dictionaries containing recommended items
    """
    cache_key = f"user_recommendations:{user_id}"
    cached_recommendations = redis_client.get(cache_key)
    
    if cached_recommendations:
        logger.info("Cache hit for user_id: {}", user_id)
        return json.loads(cached_recommendations)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{RECOMMENDATION_SERVICE_URL}/{user_id}",
                params={"num_recommendations": num_recommendations},
            )
            response.raise_for_status()
            redis_client.setex(cache_key, 3600, json.dumps(response.json()))
            logger.info(
                "Cache miss; fetched data from recommendation service for user_id: {}", user_id
            )
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error occurred: {}", e)
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
