# JARVIS - AI Personal Assistant

A sophisticated AI personal assistant powered by advanced language models, featuring voice control, vision capabilities, and an extensible plugin system.

```
┌─────────────────────────────────────────────────────────────────┐
│                        JARVIS Architecture                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐                │
│  │  Electron │────▶│ Frontend │────▶│ Backend  │                │
│  │  Desktop  │     │  (React) │     │  (FastAPI)│                │
│  └──────────┘     └──────────┘     └──────────┘                │
│                          │                  │                    │
│                          │                  ▼                    │
│                          │         ┌──────────────┐             │
│                          │         │   AI Engine   │             │
│                          │         │  (LLM/Vision) │             │
│                          │         └──────────────┘             │
│                          │                  │                    │
│                          ▼                  ▼                    │
│                   ┌────────────┐    ┌────────────┐             │
│                   │   Redis    │    │ PostgreSQL │             │
│                   │   Cache    │    │ Database   │             │
│                   └────────────┘    └────────────┘             │
│                          │                  │                    │
│                          ▼                  ▼                    │
│                   ┌─────────────────────────────┐              │
│                   │      Plugin System          │              │
│                   │  Weather | News | Calculator │              │
│                   └─────────────────────────────┘              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **Natural Language Processing**: Advanced conversational AI using GPT-4
- **Voice Control**: Speech recognition and text-to-speech
- **Vision System**: Screen capture, image analysis, OCR, face detection
- **Notes System**: Create, search, and manage notes with full-text search
- **Plugin Architecture**: Extensible plugin system with built-in plugins
- **Cross-Platform**: Desktop (Electron), Web, and CLI interfaces
- **Docker Support**: Complete containerization for easy deployment

## Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 14+
- Redis 7+
- Docker & Docker Compose (optional)

## Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/jarvis.git
cd jarvis

# Copy environment file
cp .env.example .env

# Edit .env with your API keys
nano .env

# Start all services
make docker-up

# Access the application
open http://localhost:3000
```

### Manual Setup

```bash
# Backend setup
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

pip install -r backend/requirements.txt

# Frontend setup
cd frontend
npm install
cd ..

# Database setup
createdb jarvis_db
make migrate

# Start services
make dev
```

## Development

```bash
# Install all dependencies
make install

# Start development servers
make dev

# Run tests
make test

# Run linting
make lint

# Format code
make format
```

## Configuration

Environment variables can be configured in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://jarvis:jarvis@localhost:5432/jarvis_db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SECRET_KEY` | Application secret key | Required |
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `WEATHER_API_KEY` | OpenWeatherMap API key | Optional |
| `NEWS_API_KEY` | NewsAPI key | Optional |

## API Documentation

Detailed API documentation is available at [docs/API.md](docs/API.md).

### Core Endpoints

- `POST /api/chat` - Send message to JARVIS
- `GET /api/notes` - List notes
- `POST /api/notes` - Create note
- `GET /api/plugins` - List plugins
- `POST /api/plugins/{name}/execute` - Execute plugin action

## Plugin Development

Create custom plugins by extending `BasePlugin`:

```python
from plugins.base import BasePlugin

class MyPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "my-plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "My custom plugin"

    @property
    def author(self) -> str:
        return "Your Name"

    async def execute(self, action: str, **kwargs) -> Any:
        if action == "hello":
            return "Hello from my plugin!"
        raise ValueError(f"Unknown action: {action}")

    def get_capabilities(self) -> List[str]:
        return ["hello"]
```

## Project Structure

```
JARVIS/
├── backend/           # Python FastAPI backend
├── frontend/          # React frontend application
├── electron/          # Electron desktop wrapper
├── vision/            # Computer vision system
├── notes/             # Notes management system
├── plugins/           # Plugin system
│   └── builtin/      # Built-in plugins
├── docker/            # Docker configurations
├── docs/              # Documentation
├── tests/             # Test suite
└── .github/           # CI/CD workflows
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for GPT-4 API
- FastAPI for the backend framework
- React for the frontend
- Electron for desktop support
