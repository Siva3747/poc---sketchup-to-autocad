# Python Backend Dockerfile
FROM python:3.11-slim

# Install system dependencies for shapely (GEOS) and ezdxf
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . /app/backend

# Create upload folder
RUN mkdir -p /app/backend/uploads

WORKDIR /app/backend

# Run FastAPI
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
