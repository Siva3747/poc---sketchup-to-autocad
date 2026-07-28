# Production React Frontend Dockerfile
# Stage 1: Build the app
FROM node:20-slim AS builder

WORKDIR /app

# Copy package configurations and install
COPY package.json .
RUN npm install

# Copy source and build
COPY . .
RUN npm run build

# Stage 2: Serve using Nginx
FROM nginx:alpine

# Copy custom nginx configuration if needed, or default
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
