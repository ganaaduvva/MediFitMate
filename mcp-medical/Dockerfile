# Use Node.js 20 slim as base
FROM node:20-slim

# Set working directory
WORKDIR /app

# Install system dependencies (for Puppeteer Chromium)
RUN apt-get update && \
    apt-get install -y \
    gconf-service \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcairo2 \
    libcups2 \
    libfontconfig1 \
    libgdk-pixbuf2.0-0 \
    libgbm-dev \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy rest of the source code
COPY . .

# Build TypeScript
RUN npm run build

# Verify build was successful
RUN ls -la build/

EXPOSE 8000

# Run the MCP server
CMD ["npm", "run", "start:http"]