# imagem base oficial do Python
FROM python:3.11-slim

# configurações para Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# diretório de trabalho dentro do container
WORKDIR /app

# dependências de sistema (MySQL, compiladores)
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# copia o arquivo de dependências
COPY requirements.txt .

# instala dependências Python
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# copia o restante do projeto para dentro do container
COPY . .

# porta padrão do Cloud Run
EXPOSE 8080

# comando de inicialização
CMD ["gunicorn", "managerontec.wsgi:application", "--bind", "0.0.0.0:8080"]