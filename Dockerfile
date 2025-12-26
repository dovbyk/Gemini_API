
FROM python:3.9-slim

# Install system dependencies if needed (add only what you require)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libfreetype6 \
    potrace \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /genai-backend

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

EXPOSE 5000

# Adjust the command as per your entry point
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "server:app", "--timeout", "300"]
