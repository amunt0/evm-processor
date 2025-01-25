FROM python:3.9-slim

WORKDIR /app

# Copy application code and requirements
COPY requirements.txt .
COPY block_processor.py .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "block_processor.py"]
