FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# The entrypoint runs init_db() then starts the Flask server
CMD ["python", "app.py"]
