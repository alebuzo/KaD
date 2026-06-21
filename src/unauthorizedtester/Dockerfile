# Copyright 2026 Zero Trust Demo
#
# Dockerfile para el servicio unauthorized-tester
# Este servicio intenta llamar a paymentservice y será bloqueado por Istio

FROM node:20-alpine

WORKDIR /app

# Copiar archivos de dependencias
COPY package*.json ./

# Instalar dependencias
RUN npm install --only=production

# Copiar código fuente
COPY . .

# Exponer puerto
EXPOSE 8080

# Ejecutar la aplicación
CMD ["npm", "start"]
