#!/bin/sh

echo "⏳ Aguardando o PostgreSQL iniciar..."

# Espera até que o serviço de banco de dados esteja disponível
while ! nc -z db 5432; do
  sleep 1
done

echo "✅ PostgreSQL está no ar — iniciando a API"

# Inicia a aplicação
python main.py
