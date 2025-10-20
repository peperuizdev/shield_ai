# frontend/Dockerfile
# Etapa 1: Build
FROM node:18-alpine AS builder

WORKDIR /app

# Copiar package.json y package-lock.json
COPY package*.json ./

# Instalar dependencias
RUN npm ci

# Copiar el resto del código
COPY . .

# Build de la aplicación
# Si es React (Create React App):
RUN npm run build

# Si es Next.js, usa:
# RUN npm run build

# Etapa 2: Production
FROM nginx:alpine

# Copiar el build al servidor nginx
# Para React:
COPY --from=builder /app/build /usr/share/nginx/html

# Para Next.js necesitarías una configuración diferente:
# FROM node:18-alpine
# WORKDIR /app
# COPY --from=builder /app/package*.json ./
# COPY --from=builder /app/.next ./.next
# COPY --from=builder /app/public ./public
# COPY --from=builder /app/node_modules ./node_modules
# EXPOSE 3000
# CMD ["npm", "start"]

# Copiar configuración personalizada de nginx (opcional)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Exponer puerto 80
EXPOSE 80

# Comando para ejecutar nginx
CMD ["nginx", "-g", "daemon off;"]