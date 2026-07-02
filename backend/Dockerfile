FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY fc_dream.py ./fc_dream.py

EXPOSE 8000
# Alibaba Cloud ECS / Function Compute custom-container entrypoint.
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
