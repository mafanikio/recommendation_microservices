import io
import os

import httpx
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI
from loguru import logger
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

load_dotenv()

app = FastAPI()


class RecommendationResponse(BaseModel):
    """Model for recommendation response."""
    user_id: int
    recommendations: list[dict[str, str | int]]


async def fetch_data() -> pd.DataFrame:
    """Fetch user interaction data from an external service.

    Returns:
        pd.DataFrame: User interaction data as a DataFrame.
    """
    user_data_service_url = os.getenv("USER_DATA_SERVICE_URL")
    interaction_endpoint = "/interactions"
    full_url = f"{user_data_service_url}{interaction_endpoint}"
    async with httpx.AsyncClient() as client:
        response = await client.get(full_url)
        response.raise_for_status()
        csv_data = response.text
        return pd.read_csv(io.StringIO(csv_data), sep=';')


def create_user_profile(user_id: int, user_data: pd.DataFrame, tfidf_vectorizer: TfidfVectorizer) -> np.ndarray:
    """Create a user profile based on their interactions.

    Args:
        user_id (int): The ID of the user.
        user_data (pd.DataFrame): User interaction data.
        tfidf_vectorizer (TfidfVectorizer): TF-IDF vectorizer.

    Returns:
        np.ndarray: User profile as a NumPy array.
    """
    user_interactions = user_data[user_data["user_id"] == user_id]
    user_features = tfidf_vectorizer.transform(user_interactions["combined_features"])
    user_profile = user_features.mean(axis=0)
    
    if isinstance(user_profile, np.matrix):
        return np.asarray(user_profile)
    else:
        return user_profile.toarray()


def recommend_content_based(
    user_profile: np.ndarray, tfidf_matrix: np.ndarray, top_recommendations: int,
    unique_combined_features: np.ndarray, product_mapping: dict[str, int]
) -> list[dict[str, str]]:
    """Recommend products to a user based on content-based filtering.

    Args:
        user_profile (np.ndarray): User profile.
        tfidf_matrix (np.ndarray): TF-IDF matrix of product features.
        top_recommendations (int): Number of top recommendations to generate.
        unique_combined_features (np.ndarray): Unique combined features of products.
        product_mapping (dict[str, int]): Mapping from combined features to product IDs.

    Returns:
        list[dict[str, str]]: List of recommended products with IDs and names.
    """
    similarities = linear_kernel(user_profile, tfidf_matrix)
    similar_indices = similarities.argsort()[0][-top_recommendations:][::-1]
    
    recommended_products = [
        {"id": product_mapping[unique_combined_features[i]], "name": unique_combined_features[i]}
        for i in similar_indices
    ]
    
    return recommended_products


# Content-based recommendation endpoint
@app.get("/recommend/{user_id}")
async def content_recommend(user_id: int, top_recommendations: int = 5):
    """Generate content-based recommendations for a user.

    Args:
        user_id (int): The ID of the user.
        top_recommendations (int, optional): Number of top recommendations to generate. Defaults to 5.

    Returns:
        RecommendationResponse: Recommendation response.
    """
    user_data = await fetch_data()
    
    # Processing product features (category and tags)
    user_data["combined_features"] = user_data["category"] + " " + user_data["tags"]
    tfidf_vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = tfidf_vectorizer.fit_transform(user_data["combined_features"].unique())
    unique_combined_features = user_data["combined_features"].unique()
    
    # Create a mapping from combined features to product IDs
    product_mapping = {row["combined_features"]: row["product_id"] for index, row in user_data.iterrows()}
    
    user_profile = create_user_profile(user_id, user_data, tfidf_vectorizer)
    
    # Recommend products based on the user profile
    recommended_products = recommend_content_based(
        user_profile, tfidf_matrix, top_recommendations, unique_combined_features, product_mapping
    )
    logger.info(f"Generated content-based recommendations for user_id: {user_id}")
    return RecommendationResponse(user_id=user_id, recommendations=recommended_products)
