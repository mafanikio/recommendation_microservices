# E-Commerce Microservices Project

## Description

This project implements a microservices architecture for an e-commerce platform, focusing on providing personalized
product recommendations to users. It consists of three main microservices:

1. **User Service**: Manages user data and interactions.
2. **Recommendation Service**: Generates product recommendations based on user history using a content-based filtering
   algorithm.
3. **Client Service**: Acts as an intermediary, handling client requests, API key authentication, and caching.

## Prerequisites

- Docker and Docker Compose
- Python 3.11 or higher
- Poetry for Python dependency management

## Installation and Setup

1. **Clone the Repository**:
   ```bash
   git clone [repository-url]
   cd [repository-directory]

2 **Update the .env file with necessary environment variables
like `REDIS_HOST`, `MONGO_URI`, `RECOMMENDATION_SERVICE_URL`, etc.**

3 **Building the Docker Images:**

   ```bash
   docker-compose build
   ```

4 **Running the Docker Containers:**

```bash
 docker-compose up 
 ```

5 **Filling mongo with data:**

```bash
   docker exec -it <container_name> /bin/bash
   python db_filler.py
  ```

## Accessing the Services

Client Service: http://127.0.0.1:8000/recommend/<user_id>
