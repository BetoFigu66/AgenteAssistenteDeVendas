FROM python:3.11-slim

WORKDIR /app

# Copiar requirements e instalar dependências
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fonte
COPY backend/ .

# Criar diretório de dados
RUN mkdir -p data

# Expor porta
EXPOSE 8000

# Comando para iniciar
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
