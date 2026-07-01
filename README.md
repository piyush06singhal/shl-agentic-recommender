# Conversational SHL Assessment Recommender

> **A Production-Ready AI-Powered Conversational Agent for Talent Assessment Discovery**

[![CI/CD Pipeline](https://github.com/username/shl-recommender/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/username/shl-recommender/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 16](https://img.shields.io/badge/next.js-16-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Live Demo:** 🚀 [Coming Soon]

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running Locally](#running-locally)
- [Docker Deployment](#docker-deployment)
- [Testing](#testing)
- [API Documentation](#api-documentation)
- [Frontend Usage](#frontend-usage)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Future Enhancements](#future-enhancements)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

Conversational AI Agent system designed to help recruiters discover suitable candidate assessments from the official SHL Individual Test Solutions catalog. The assistant functions as a talent acquisition hiring consultant, probing for criteria, evaluating constraints, and performing direct test comparisons.

Built with modern technologies and production-ready practices, this system demonstrates:

- ✅ **Retrieval-Augmented Generation (RAG)** pattern implementation
- ✅ **Stateless architecture** with dynamic context reconstruction
- ✅ **Vector-based semantic search** using ChromaDB
- ✅ **Hybrid scoring** (keywords + metadata + semantic similarity)
- ✅ **Production-grade error handling** and logging
- ✅ **Comprehensive test coverage** (unit + integration + e2e)
- ✅ **Docker containerization** for easy deployment
- ✅ **CI/CD pipeline** with GitHub Actions

---

## ✨ Key Features

### 🤖 Intelligent Conversation Management

- **Intent Detection**: Automatically classifies user queries (greeting, clarification, recommendation, comparison, refinement)
- **Context Extraction**: Dynamically reconstructs requirements from conversation history
- **Stateless Design**: No session storage required - all context derived from message history

### 🔍 Advanced Retrieval System

- **Vector Search**: Semantic similarity using OpenAI embeddings (text-embedding-3-small)
- **Keyword Matching**: Exact term matching for precise results
- **Metadata Filtering**: Filter by job family, seniority level, duration, languages
- **Hybrid Scoring**: Combines multiple relevance signals for optimal ranking

### 💬 Natural Conversation Flow

- **Clarification Prompts**: Asks follow-up questions when requirements are incomplete
- **Recommendations**: Provides 1-10 ranked assessment suggestions
- **Comparisons**: Side-by-side feature analysis of multiple tests
- **Refinement**: Iteratively narrows results based on feedback

### 🎨 Modern Frontend

- **Dark/Light Theme**: User-preference based theming
- **Developer Mode**: Real-time debug telemetry and system logs
- **Health Dashboard**: Live backend status monitoring
- **Responsive Design**: Mobile-first Tailwind CSS styling
- **Smooth Animations**: Framer Motion transitions

---

## 🏗️ Architecture

The application follows a **Retrieval-Augmented Generation (RAG)** pattern with stateless request processing:

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Client                             │
│                   (Next.js Frontend App)                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ POST /chat
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐     ┌──────────────┐     ┌────────────────┐  │
│  │   API Layer │────▶│   Parser     │────▶│  Intent        │  │
│  │             │     │              │     │  Classifier    │  │
│  └─────────────┘     └──────────────┘     └────────┬───────┘  │
│                                                     │           │
│                            ┌────────────────────────┘           │
│                            ▼                                    │
│                   ┌─────────────────┐                          │
│                   │ Context Builder │                          │
│                   └────────┬────────┘                          │
│                            ▼                                    │
│                   ┌─────────────────┐                          │
│                   │ Decision Engine │                          │
│                   └────┬────────┬───┘                          │
│                        │        │                               │
│              Complete? │        │ Incomplete?                   │
│                        ▼        ▼                               │
│             ┌──────────────┐   ┌────────────────┐             │
│             │  Retriever   │   │  LLM Service   │             │
│             │    Engine    │   │ (Clarification)│             │
│             └──────┬───────┘   └────────────────┘             │
│                    ▼                                            │
│         ┌────────────────────┐                                 │
│         │  Vector Store      │                                 │
│         │  (ChromaDB)        │                                 │
│         └──────┬─────────────┘                                 │
│                ▼                                                │
│         ┌────────────────────┐                                 │
│         │  LLM Service       │                                 │
│         │ (Recommendation)   │                                 │
│         └──────┬─────────────┘                                 │
│                ▼                                                │
│         ┌────────────────────┐                                 │
│         │  Response          │                                 │
│         │  Validator         │                                 │
│         └────────────────────┘                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

1. **API Layer**: FastAPI routes with request/response validation
2. **Conversation Parser**: Extracts user/assistant turns from history
3. **Intent Classifier**: Categorizes query type using LLM
4. **Context Builder**: Reconstructs active search criteria from messages
5. **Decision Engine**: Routes to retrieval or clarification path
6. **Retrieval Engine**: Hybrid search across vector database
7. **LLM Service**: OpenAI GPT integration for generation
8. **Response Validator**: Ensures output schema compliance

---

## 🛠️ Tech Stack

### Backend

- **Framework**: FastAPI 0.100+
- **Language**: Python 3.12+
- **Vector Database**: ChromaDB
- **LLM Provider**: OpenAI (GPT-4o, text-embedding-3-small)
- **Data Validation**: Pydantic v2
- **Testing**: Pytest with async support
- **Code Quality**: Ruff, Black, isort, MyPy

### Frontend

- **Framework**: Next.js 16 (App Router)
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS 4
- **Animations**: Framer Motion
- **HTTP Client**: Axios
- **State Management**: React Query (@tanstack/react-query)
- **Icons**: Lucide React

### DevOps

- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Deployment**: Render, Vercel, Railway
- **Logging**: Python logging with rotating file handlers
- **Monitoring**: Health check endpoints

---

## 📦 Prerequisites

- **Python 3.12+** ([Download](https://www.python.org/downloads/))
- **Node.js 20+** ([Download](https://nodejs.org/))
- **Docker** (optional, for containerized deployment) ([Download](https://www.docker.com/))
- **OpenAI API Key** ([Get API Key](https://platform.openai.com/api-keys))

---

## 🚀 Installation

### 1. Clone Repository

```bash
git clone https://github.com/username/shl-recommender.git
cd shl-recommender
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

---

## ⚙️ Configuration

### Backend Configuration

1. Copy environment template:

```bash
cp .env.example .env
```

2. Edit `.env` with your credentials:

```env
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# LLM Models Configuration
MODEL_NAME=gpt-4o
EMBEDDING_MODEL=text-embedding-3-small

# Search & Retrieval Configuration
TOP_K=15
SIMILARITY_THRESHOLD=0.70

# Latency and System Settings
API_TIMEOUT=25.0
LOG_LEVEL=INFO

# Server Configuration
HOST=0.0.0.0
PORT=8000

# CORS Configuration (comma-separated)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
ALLOWED_HOSTS=*
```

### Frontend Configuration

1. Create frontend environment file:

```bash
cd frontend
cp .env.local .env.local
```

2. Edit `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 🖥️ Running Locally

### Option 1: Run Backend and Frontend Separately

**Terminal 1 - Backend:**

```bash
# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run backend
python scripts/run.py
# Backend will start at http://localhost:8000
```

**Terminal 2 - Frontend:**

```bash
cd frontend
npm run dev
# Frontend will start at http://localhost:3000
```

### Option 2: Use Makefile (Backend only)

```bash
make install  # Install dependencies
make run      # Start backend server
make test     # Run tests
make lint     # Run linters
make format   # Format code
make clean    # Clean cache files
```

---

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Build and start all services
docker-compose up --build

# Run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Using Docker (Backend only)

```bash
# Build image
docker build -t shl-recommender:latest .

# Run container
docker run -p 8000:8000 --env-file .env shl-recommender:latest
```

---

## 🧪 Testing

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=app --cov-report=html
```

### Run Specific Test Files

```bash
# API tests
pytest tests/test_api.py -v

# Production integration tests
pytest tests/test_production_integration.py -v

# Agent tests
pytest tests/test_agent.py -v
```

### Run Frontend Linting

```bash
cd frontend
npm run lint
```

---

## 📚 API Documentation

### Interactive API Docs

Once the backend is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Core Endpoints

#### `GET /health`

Health check endpoint for monitoring.

**Response:**

```json
{
  "status": "ok"
}
```

#### `POST /chat`

Main conversational endpoint.

**Request:**

```json
{
  "messages": [
    {
      "role": "user",
      "content": "I need a test for software engineers"
    }
  ]
}
```

**Response:**

```json
{
  "reply": "I can help you find suitable assessments...",
  "recommendations": [
    {
      "name": "Verify G+ Cognitive Assessment",
      "url": "https://shl.com/verify",
      "test_type": "Cognitive"
    }
  ],
  "end_of_conversation": false
}
```

---

## 🎨 Frontend Usage

### Features

1. **Landing Page**: Overview of system capabilities
2. **Chat Interface**: Conversational interaction with AI agent
3. **Health Dashboard**: Real-time system status monitoring
4. **Developer Mode**: Debug telemetry and raw response inspection
5. **Dark/Light Theme**: Toggle between themes
6. **Settings Panel**: Configure backend API URL

### Navigation

- **Overview Tab**: Project introduction and architecture
- **Consultant Chat Tab**: Main chat interface
- **Health Check Tab**: System diagnostics

### Quick Start Prompts

- "I need a test for software engineers"
- "Compare OPQ and Verify tests"
- "Show me personality assessments"
- "What tests are available for graduates?"

---

## 🚢 Deployment

### Deploy Backend to Render

1. Create account at [render.com](https://render.com)
2. Connect your GitHub repository
3. Create new Web Service
4. Use existing `render.yaml` configuration
5. Set environment variables in Render dashboard
6. Deploy!

### Deploy Frontend to Vercel

1. Create account at [vercel.com](https://vercel.com)
2. Import your GitHub repository
3. Framework will be auto-detected as Next.js
4. Set environment variable:
   - `NEXT_PUBLIC_API_URL`: Your backend URL
5. Deploy!

### Deploy to Railway

1. Create account at [railway.app](https://railway.app)
2. Create new project from GitHub repo
3. Railway will use `railway.json` configuration
4. Set environment variables
5. Deploy!

---

## 📁 Project Structure

```
shl-recommender/
├── app/
│   ├── agent/              # Core conversational agent logic
│   │   ├── agent.py        # Main agent orchestrator
│   │   ├── classifier.py   # Intent classification
│   │   ├── context.py      # Context extraction
│   │   ├── decision.py     # Routing decision engine
│   │   └── parser.py       # Conversation history parser
│   ├── api/                # FastAPI routes and middleware
│   │   ├── routes/
│   │   │   ├── chat.py     # Chat endpoint
│   │   │   └── health.py   # Health check endpoint
│   │   ├── middleware.py   # CORS, logging, request ID
│   │   └── dependencies.py # Dependency injection
│   ├── catalog/            # Catalog management
│   │   ├── data/           # JSON catalog and vector DB
│   │   └── manager.py      # Catalog loader
│   ├── llm/                # LLM service integration
│   │   ├── service.py      # OpenAI client wrapper
│   │   └── provider.py     # Provider abstraction
│   ├── retriever/          # Retrieval engine
│   │   ├── engine.py       # Main retrieval logic
│   │   ├── vector_store.py # ChromaDB interface
│   │   └── ranker.py       # Result ranking
│   ├── schemas/            # Pydantic models
│   │   ├── request.py      # Request validation
│   │   └── response.py     # Response models
│   ├── configs/            # Configuration
│   │   ├── settings.py     # Environment settings
│   │   └── logging.py      # Logging setup
│   └── main.py             # FastAPI application
├── frontend/
│   ├── app/
│   │   ├── page.tsx        # Main application page
│   │   ├── layout.tsx      # Root layout
│   │   └── globals.css     # Global styles
│   ├── types/
│   │   └── index.ts        # TypeScript interfaces
│   ├── package.json        # Node dependencies
│   └── next.config.ts      # Next.js configuration
├── tests/
│   ├── test_api.py         # API endpoint tests
│   ├── test_agent.py       # Agent logic tests
│   ├── test_retriever.py   # Retrieval engine tests
│   └── test_production_integration.py  # E2E tests
├── scripts/
│   └── run.py              # Server startup script
├── .github/
│   └── workflows/
│       └── ci-cd.yml       # GitHub Actions pipeline
├── docker-compose.yml      # Multi-container setup
├── Dockerfile              # Backend container image
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Python project config
├── Makefile                # Development automation
├── render.yaml             # Render deployment config
├── railway.json            # Railway deployment config
└── README.md               # This file
```

---

## 🔧 Troubleshooting

### Common Issues

#### Backend won't start

**Problem**: `ModuleNotFoundError` or import errors

**Solution**:

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt
```

#### OpenAI API errors

**Problem**: `AuthenticationError` or `RateLimitError`

**Solution**:

- Verify `OPENAI_API_KEY` in `.env` is correct
- Check API key has available credits
- Check for rate limit issues in OpenAI dashboard

#### Frontend can't connect to backend

**Problem**: Network errors, CORS issues

**Solution**:

- Verify backend is running on `http://localhost:8000`
- Check `NEXT_PUBLIC_API_URL` in `frontend/.env.local`
- Verify CORS settings in `app/api/middleware.py`

#### Vector database errors

**Problem**: ChromaDB connection issues

**Solution**:

```bash
# Ensure vector database exists
ls app/catalog/data/vector_db/

# If missing, rebuild catalog
python -c "from app.catalog.manager import CatalogManager; CatalogManager()"
```

#### Docker build fails

**Problem**: Build context errors

**Solution**:

```bash
# Clean Docker cache
docker system prune -a

# Rebuild without cache
docker-compose build --no-cache
```

---

## 🔮 Future Enhancements

- [ ] **Multi-language Support**: Internationalization for non-English speakers
- [ ] **Advanced Analytics**: Usage tracking and recommendation metrics
- [ ] **User Authentication**: Personalized recommendations and history
- [ ] **Streaming Responses**: Real-time token streaming for faster perceived latency
- [ ] **Voice Interface**: Speech-to-text for conversational input
- [ ] **Export Features**: PDF reports of recommended assessments
- [ ] **Admin Dashboard**: Content management and analytics
- [ ] **A/B Testing**: Experiment with different retrieval strategies
- [ ] **Caching Layer**: Redis for frequent queries
- [ ] **Rate Limiting**: Prevent API abuse

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide for Python code
- Use TypeScript for frontend code
- Write tests for new features
- Update documentation as needed
- Run linters before committing:
  ```bash
  make lint    # Backend
  cd frontend && npm run lint  # Frontend
  ```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📞 Contact

**Project Author**: [Your Name]

- Email: your.email@example.com
- LinkedIn: [your-profile](https://linkedin.com/in/your-profile)
- GitHub: [@username](https://github.com/username)

**Project Link**: [https://github.com/username/shl-recommender](https://github.com/username/shl-recommender)

---

## 🙏 Acknowledgments

- [SHL](https://www.shl.com/) for the assessment catalog
- [OpenAI](https://openai.com/) for GPT and embedding models
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [Next.js](https://nextjs.org/) for the React framework
- [ChromaDB](https://www.trychroma.com/) for vector database

---

<div align="center">

**⭐ Star this repo if you find it helpful!**

Made with ❤️ for talent acquisition professionals

</div>
