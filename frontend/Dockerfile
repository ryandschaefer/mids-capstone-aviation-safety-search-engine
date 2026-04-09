# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies (npm install tolerates lock/file mismatch; npm ci would require exact sync)
RUN npm install

# Copy source code
COPY . .

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine AS production

# Copy built assets from build stage
COPY --from=build /app/build /usr/share/nginx/html

# Copy custom nginx config
COPY src/nginx.conf /etc/nginx/conf.d/default.conf

# Copy env injection script — nginx runs this on startup before serving requests
COPY react_env.sh /docker-entrypoint.d/react_env.sh
RUN chmod +x /docker-entrypoint.d/react_env.sh

# Create non-root user
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser && \
    chown -R appuser:appuser /usr/share/nginx/html && \
    chown -R appuser:appuser /var/cache/nginx && \
    chown -R appuser:appuser /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R appuser:appuser /var/run/nginx.pid

USER appuser

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]