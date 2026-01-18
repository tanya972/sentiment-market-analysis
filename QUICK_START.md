# Quick Start Guide

## Step 1: Prerequisites

Install Docker Desktop:
- Mac: https://docs.docker.com/desktop/install/mac-install/
- Windows: https://docs.docker.com/desktop/install/windows-install/

## Step 2: Setup

```bash
# Navigate to project
cd sentiment-market-alerts

# Create environment file
cp .env.example .env

# Start all services
docker-compose up --build
```

Wait for: "✅ Application started successfully!"

## Step 3: Test

Open browser: http://localhost:8000/docs

Or test with curl:
```bash
curl http://localhost:8000/health
```

## What's Running

- API Server: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Background Workers: Automatic

## View Logs

```bash
# All logs
docker-compose logs -f

# Just API
docker-compose logs -f api

# Just workers
docker-compose logs -f worker
```

## Stop Everything

```bash
docker-compose down
```

## Troubleshooting

**Port already in use:**
```bash
docker-compose down
docker-compose up
```

**Start fresh:**
```bash
docker-compose down -v
docker-compose up --build
```

## Next Steps

1. Read the code (start with api/main.py)
2. Test the endpoints (/docs)
3. Watch workers in logs
4. Customize for your needs

You're ready to interview! 🚀
