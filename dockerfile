# Imagen base ligera de Python 3.10, ideal para ML y APIs
FROM python:3.10-slim

# Instala dependencias del sistema necesarias para ML, Redis y compatibilidad con algunas librerías (OpenCV, etc.)
RUN apt-get update && \
    apt-get install -y gcc g++ libgl1 libpq-dev curl libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /backend

# Copia la carpeta backend completa (incluye app, tests, utils, requirements.txt, main.py, etc.)
COPY backend/ ./

# Copia la carpeta de monitoreo (monitoring) para configuración y dashboards
COPY monitoring/ ./monitoring/

# Instala las dependencias Python especificadas en requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia archivos de configuración opcionales si existen (por ejemplo, .env)
# COPY .env .env

# Expone el puerto 8000 para la API FastAPI/Uvicorn
EXPOSE 8000

# Expone el puerto 3000 para Grafana (monitoring)
EXPOSE 3000

# Expone el puerto 9090 para Prometheus (monitoring)
EXPOSE 9090

# Configura la variable de entorno PYTHONPATH para que los imports funcionen correctamente (especialmente 'core')
ENV PYTHONPATH=/backend/app

# Comando de inicio: ejecuta el servidor Uvicorn con la aplicación FastAPI
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Sugerencia: para producción, puedes agregar gunicorn o usar workers
# Ejemplo: CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8000"]