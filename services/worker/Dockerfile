FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
COPY shared ./shared
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
CMD ["python", "-m", "app.worker"]
