# LockNIn container image.
# Multi-stage build: stage 1 compiles the React frontend with Node, stage 2 is
# the Python runtime that actually ships. The final image contains no Node,
# node_modules, or TypeScript source, only the compiled frontend/dist and the
# Flask app. Keeps the image small and the runtime surface tiny.

# ---- Stage 1: build the React frontend ------------------------------------
# Base images are pulled from AWS ECR Public, which mirrors the identical
# Docker official images. Railway's builder intermittently times out reaching
# Docker Hub (registry-1.docker.io), and ECR Public also sidesteps Hub's
# anonymous pull rate limits. Swap back to `node:22-alpine` if ever needed.
FROM public.ecr.aws/docker/library/node:22-alpine AS frontend
WORKDIR /build

# Copy only the lockfiles first so `npm ci` is cached until deps change.
# Docker skips a layer when its inputs are unchanged since the last build.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# `npm run build` runs `tsc -b && vite build`, which needs devDependencies,
# so `npm ci` above deliberately does not use --omit=dev.
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python runtime ----------------------------------------------
FROM public.ecr.aws/docker/library/python:3.13-slim
WORKDIR /app

# Same caching trick: deps before code, so editing app.py doesn't reinstall pip.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY migrations/ ./migrations/
COPY static/ ./static/

# Pull the compiled frontend out of stage 1. Flask serves this directory
# (static_folder='frontend/dist' in app.py), so the path must match exactly.
COPY --from=frontend /build/dist/ ./frontend/dist/

# Documents the port Railway routes to (its default target port). Not enforced
# by Docker, but keeps the contract visible to whoever reads this file.
EXPOSE 8080

# Runs on container start, not build. Shell form so ${PORT} expands.
#
# Migration step: PGOPTIONS sets a Postgres lock_timeout so a migration blocked
# by another session fails fast with a clear error instead of hanging forever
# (which silently prevented gunicorn from ever starting). `timeout 120` is a
# hard backstop. If the step fails we log loudly and still start the server,
# so a transient DB hiccup doesn't take the whole site down. Watch Deploy Logs
# for the "!!!" line and fix the cause; do not treat it as normal.
#
# Railway injects PORT at runtime; 8080 matches Railway's default if it doesn't.
# Bind to [::] (dual-stack), NOT 0.0.0.0: Railway's edge proxy reaches the
# container over IPv6, and 0.0.0.0 only listens on IPv4, so every request
# would time out with "connection dial timeout" / 502.
# `exec` makes gunicorn PID 1 so it receives Railway's stop signals directly.
CMD PGOPTIONS="-c lock_timeout=30s -c statement_timeout=90s" timeout 120 flask db upgrade || echo "!!! flask db upgrade failed or timed out (exit $?); starting server anyway"; exec gunicorn --worker-class gthread -w 1 --threads 4 --bind [::]:${PORT:-8080} app:app
