FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set default deployment type
ENV DEPLOYMENT=Stable

COPY . .

CMD ["python", "app.py"]
