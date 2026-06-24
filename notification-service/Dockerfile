FROM python:3.11-slim

WORKDIR /app

# Instala nc (netcat) para o wait-for-db.sh
RUN apt-get update && \
    apt-get install -y netcat-openbsd && \
    apt-get clean

# Instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY ./app ./app
COPY wait-for-db.sh .
COPY main.py .
COPY init_db.py .
COPY openapi ./openapi

# Dá permissões de execução ao script
RUN chmod +x wait-for-db.sh

# Comando de inicialização
CMD ["gunicorn", "-b", "0.0.0.0:8001", "main:application"]
