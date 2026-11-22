FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir flask==3.1.0

COPY app.py .

# data_path = /data — persistent volume for checklist state
RUN mkdir -p /data

EXPOSE 80

CMD ["python", "app.py"]
