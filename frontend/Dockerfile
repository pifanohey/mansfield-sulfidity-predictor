# Frontend Dockerfile for Sulfidity Predictor
# Multi-stage build for smaller production image

# Stage 1: Build the application
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Set the API URL for production build
ENV NEXT_PUBLIC_API_URL=http://localhost:8000

# Build the application
RUN npm run build

# Stage 2: Production image
FROM node:18-alpine AS runner

WORKDIR /app

# Set to production
ENV NODE_ENV=production

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built application from builder stage
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Set correct permissions
USER nextjs

# Expose port
EXPOSE 3000

# Set hostname
ENV HOSTNAME="0.0.0.0"

# Run the application
CMD ["node", "server.js"]
