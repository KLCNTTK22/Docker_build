FROM python:3.10-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir flask werkzeug

EXPOSE 5000

CMD ["python", "app.py"]