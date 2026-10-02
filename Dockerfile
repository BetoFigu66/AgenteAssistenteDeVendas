FROM python:3.11-slim

# O código chega por bind mount só leitura (docker-compose), então o Python não
# consegue gravar __pycache__ ali; sem esta variável ele tentaria a cada import.
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copiar requirements e instalar dependências
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Usuário sem privilégio (I3): o processo só escreve em logs/ (volume) e em /tmp.
RUN useradd --uid 1000 --create-home app

# Copiar código fonte
COPY backend/ .

# logs/ é o ponto de montagem do volume `backend_logs`. O dono é definido aqui
# porque o Docker copia dono e permissões da imagem para o volume na primeira vez
# que ele é montado; sem isso o volume nasceria de root e o `app` não gravaria.
RUN mkdir -p data logs && chown app:app logs

USER app

# Expor porta
EXPOSE 8000

# Comando para iniciar
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
