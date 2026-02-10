# Frontend Dockerfile - multi-stage build
FROM node:22-alpine AS build

WORKDIR /app
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Production - serve with nginx
FROM nginx:alpine AS production
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
