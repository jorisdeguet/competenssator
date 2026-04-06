FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for reportlab and svglib
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create results directory
RUN mkdir -p results

EXPOSE 5000

ENV FLASK_APP=app.py
ENV SECRET_KEY=change-me-in-production

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
