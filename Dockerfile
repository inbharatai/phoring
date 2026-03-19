# ── Stage 1: Build Vue frontend ─────────────────────────────────────────────
FROM node:20-alpine AS frontend-build

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Production Python image ───────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install backend Python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy built frontend into backend static serving directory
COPY --from=frontend-build /build/dist ./frontend/dist

# Copy root files needed at runtime
COPY run.py ./

# Ensure uploads directory exists
RUN mkdir -p backend/uploads/projects backend/uploads/reports \
    backend/uploads/simulations backend/uploads/tasks

EXPOSE 10000

# Render uses PORT env var; default to 10000
ENV PORT=10000

CMD ["python", "backend/run.py"]