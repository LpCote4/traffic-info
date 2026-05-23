FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

# Start both the monitor and the web dashboard
CMD ["sh", "-c", "uvicorn web.server:app --host 0.0.0.0 --port 8080 & python main.py"]
