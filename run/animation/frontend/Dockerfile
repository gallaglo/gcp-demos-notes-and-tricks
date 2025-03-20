FROM node:18-alpine AS builder
WORKDIR /app

# First copy only package files to leverage cache for npm ci
COPY package*.json ./
RUN npm ci

# Copy configuration files
COPY *.ts ./
COPY *.mjs ./
COPY *.json ./

# Copy source code
COPY app/ ./app/
COPY components/ ./components/
COPY lib/ ./lib/
COPY public/ ./public/

# Set environment variables
ENV NEXT_PUBLIC_API_URL=""

# Build the application
RUN npm run build

# Stage 2: Production environment
FROM node:18-alpine AS runner
WORKDIR /app

# Create a non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy only necessary files from builder
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Set ownership to non-root user
RUN chown -R nextjs:nodejs /app

# Switch to non-root user
USER nextjs

# Set environment variables
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=8080

EXPOSE 8080

# Start the application
CMD ["node", "server.js"]