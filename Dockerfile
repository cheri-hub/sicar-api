FROM python:3.11-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    git \
    libgdal-dev \
    gdal-bin \
    libpq-dev \
    postgresql-client \
    gcc \
    curl \
    # Dependências do OpenCV
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar SICAR package
COPY SICAR_package/ ./SICAR_package/
RUN cd SICAR_package && pip install -e .

# Copiar código da aplicação
COPY ./app ./app
COPY ./scripts ./scripts

# Criar diretórios necessários
RUN mkdir -p /app/downloads /app/logs

# Expor porta
EXPOSE 8000

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando de inicialização
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
