# Usamos una imagen de Python estándar y completa para máxima compatibilidad
FROM python:3.9-bullseye

# Instalación de drivers
RUN apt-get update && apt-get install -y curl gpg gnupg
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
RUN echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y unixodbc-dev msodbcsql18

# Proceso estándar de la aplicación
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# NO nos movemos a /app/ItemsAPI. Nos quedamos en /app para que Python vea la carpeta ItemsAPI como un paquete.

EXPOSE 80

# VOLVEMOS al comando CMD original.
# Esto le dice a Uvicorn que busque el paquete "ItemsAPI", luego el fichero "function_app"
CMD ["uvicorn", "ItemsAPI.function_app:app", "--host", "0.0.0.0", "--port", "80"]