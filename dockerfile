FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/uploads
# Crear configuracion.json por defecto si no existe (el volumen lo sobreescribirá)
RUN echo '{"precio_dolar": 0, "iva": 0, "last_version": "1.0.0"}' > /app/configuracion.json
# Declarar volúmenes para persistencia
VOLUME ["/app/uploads", "/app/configuracion.json"]
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]