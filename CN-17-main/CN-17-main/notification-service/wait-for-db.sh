#!/bin/sh

echo "⏳ Aguardando o PostgreSQL iniciar..."

# Espera até o PostgreSQL estar acessível
while ! nc -z db 5432; do
  sleep 1
done

echo "✅ PostgreSQL está no ar — iniciando a API"
exec python main.py
