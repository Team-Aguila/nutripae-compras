# PAE Menus Backend

Backend API for managing PAE (Programa de Alimentación Escolar) menus module.

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Poetry (dependency management)
- Docker and Docker Compose (for database)

### Installation

1. **Clone the repository**
   ```bash
   git clone git@github.com:Team-Aguila/pae-menus.git 
   cd pae-menus
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```
    Docs for poetry installation: https://python-poetry.org/docs/ 
3. **Start the database**
   ```bash
   docker-compose up -d
   ```

4. **Run the application**
   ```bash
   poetry run poe dev
   ```

The API will be available at `http://localhost:8001`

## 📚 API Documentation

Once the application is running, you can access the full API documentation:

- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`

## 🛠️ Development

### Environment Setup

The application uses environment variables for configuration. Create a `.env` file in the root directory if needed.

### Database

The project uses MongoDB as its database. The Docker Compose setup provides:
- MongoDB instance on port `27017`
- Default credentials: `root:example`


### Code Quality

This project uses commitizen and pre-commit for maintaining code quality and consistent commit messages.

#### Creating Commits

**Do not use regular git commits**. Instead, use:

```bash
git add .
poetry run cz commit
```

#### Managing Changelog

Create changelog (first time):
```bash
poetry run cz changelog --unreleased-version "v0.1.0"
```

Update changelog:
```bash
poetry run cz changelog
```

## 🏗️ Project Structure

```
pae-menus/
├── src/pae_menus/          # Main application code
│   ├── api/                # API routes
│   ├── core/               # Core functionality
│   ├── models/             # Data models
│   ├── services/           # Business logic
│   └── main.py             # FastAPI application
├── tests/                  # Test files
├── client_sdk/             # Client SDK
└── docker-compose.yml      # Database setup
```

