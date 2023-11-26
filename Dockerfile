# Use an official Python runtime as a parent image
FROM python:3.11 as builder

# Install system dependencies required for scikit-surprise
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libatlas-base-dev git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy the poetry configuration files into the container
WORKDIR /usr/src/app
COPY pyproject.toml poetry.lock* ./

# Install other dependencies using Poetry without creating a virtual environment
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Runtime stage
FROM python:3.11-slim

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the application code
COPY src/ ./

# Set environment variables for running the application
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1