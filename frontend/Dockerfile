# Development stage
FROM node:20-alpine AS development

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Expose port
EXPOSE 3000

# Run development server
CMD ["npm", "run", "dev", "--", "--host"]

# Production build stage
FROM node:20-bookworm-slim AS build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --prefer-offline --no-audit --ignore-scripts

# Copy application code
COPY . .

# Build argument for version (defaults to 0.1.0 if not provided)
ARG VITE_APP_VERSION=0.1.0
ENV VITE_APP_VERSION=$VITE_APP_VERSION

# Release channel baked into UI (beta workflow sets "beta"; stable builds leave empty)
ARG VITE_RELEASE_CHANNEL=
ENV VITE_RELEASE_CHANNEL=$VITE_RELEASE_CHANNEL

# Optional lab default for tablet resolution when localStorage unset (prefer per-device setup UI)
ARG VITE_TABLET_MACHINE_ID=
ENV VITE_TABLET_MACHINE_ID=$VITE_TABLET_MACHINE_ID
ARG VITE_PWA_START_URL=
ENV VITE_PWA_START_URL=$VITE_PWA_START_URL

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine AS production

# Copy built files from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Fix permissions for all files
RUN chmod -R 644 /usr/share/nginx/html/* && \
    find /usr/share/nginx/html -type d -exec chmod 755 {} \;

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Run nginx
CMD ["nginx", "-g", "daemon off;"]
