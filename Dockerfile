FROM python:3.11-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala Chromium + todas as dependências do sistema em um único passo
RUN python -m playwright install --with-deps chromium

COPY . .

CMD ["python", "main.py"]
