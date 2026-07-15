# JARVIS Setup Guide

## Prerequisites

### Required Software

| Software | Version | Download |
|----------|---------|----------|
| Python | 3.11+ | https://python.org |
| Node.js | 20+ | https://nodejs.org |
| PostgreSQL | 14+ | https://postgresql.org |
| Redis | 7+ | https://redis.io |

### Optional Software

| Software | Purpose |
|----------|---------|
| Docker | Containerized deployment |
| Git | Version control |
| Tesseract OCR | Vision system OCR |

## Platform-Specific Setup

### Windows

```powershell
# Install Python (via winget)
winget install Python.Python.3.11

# Install Node.js (via winget)
winget install OpenJS.NodeJS.LTS

# Install PostgreSQL (via winget)
winget install PostgreSQL.PostgreSQL.16

# Install Redis (via Chocolatey)
choco install redis-64

# Install Tesseract (via Chocolatey)
choco install tesseract
```

### macOS

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 node postgresql@16 redis tesseract
brew services start postgresql@16
brew services start redis
```

### Linux (Ubuntu/Debian)

```bash
# Update package list
sudo apt update

# Install Python
sudo apt install python3.11 python3.11-venv python3-pip

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Install Redis
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis

# Install Tesseract
sudo apt install tesseract-ocr
```

## Project Setup

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/jarvis.git
cd jarvis
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

### 4. Database Setup

```bash
# Create database
# Windows (via psql):
psql -U postgres -c "CREATE USER jarvis WITH PASSWORD 'jarvis';"
psql -U postgres -c "CREATE DATABASE jarvis_db OWNER jarvis;"

# macOS/Linux:
sudo -u postgres psql -c "CREATE USER jarvis WITH PASSWORD 'jarvis';"
sudo -u postgres psql -c "CREATE DATABASE jarvis_db OWNER jarvis;"

# Run migrations
make migrate
```

### 5. Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

### 6. Start Development Servers

```bash
# Start all services
make dev

# Or start individually:
# Backend (Terminal 1):
uvicorn backend.main:app --reload --port 8000

# Frontend (Terminal 2):
cd frontend && npm start
```

## Docker Setup (Alternative)

### Using Docker Compose

```bash
# Copy environment file
cp .env.example .env

# Build and start containers
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

### Development with Docker

```bash
# Use development compose file
docker-compose -f docker-compose.dev.yml up -d

# This includes:
# - Hot reloading for backend and frontend
# - Debug ports exposed
# - MailHog for email testing
```

## Verify Installation

1. Open browser to http://localhost:3000
2. Open terminal to http://localhost:8000/docs (API docs)
3. Check database: `psql -U jarvis -d jarvis_db`

## Common Issues

### Port Already in Use

```bash
# Find process using port
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # macOS/Linux

# Kill process
taskkill /PID <pid> /F        # Windows
kill <pid>                    # macOS/Linux
```

### Database Connection Failed

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql  # Linux
brew services list                # macOS

# Reset password
sudo -u postgres psql
ALTER USER jarvis WITH PASSWORD 'new_password';
```

### Redis Connection Failed

```bash
# Check Redis is running
redis-cli ping  # Should return PONG

# Start Redis
redis-server     # Manual start
sudo systemctl start redis  # Linux service
```

## Next Steps

- Read [API Documentation](API.md)
- Review [Architecture Overview](ARCHITECTURE.md)
- Check out the Plugin Development Guide in README.md
