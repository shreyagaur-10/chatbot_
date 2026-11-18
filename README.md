# DarGlobal & Wasalt AI Chatbot

An AI-powered chatbot built with data scraped from [DarGlobal](https://www.darglobal.co.uk) and [Wasalt](https://www.wasalt.com), powered by free LLMs via [OpenRouter](https://openrouter.ai), containerised with Docker.

---

## 🚀 Live Demo

**Deployed URL:** [https://chatbot-or3g.onrender.com/](https://chatbot-or3g.onrender.com/)

---

## 📋 Features

- **Web Scraping**: Automatically scrapes publicly available data from DarGlobal and Wasalt
- **RAG (Retrieval-Augmented Generation)**: TF-IDF based retrieval to find relevant context
- **Free LLM via OpenRouter**: Uses free models (`meta-llama/llama-3.1-8b-instruct:free`, etc.)
- **Docker Containerised**: Multi-stage Dockerfile for clean production builds
- **Conversational Memory**: Maintains session history for multi-turn conversations
- **Responsive UI**: Beautiful dark-themed chat interface

## 🏗️ Architecture

```
User Request
     │
     ▼
FastAPI Server
     │
     ├──► TF-IDF Retrieval Engine  ◄── DarGlobal + Wasalt Knowledge Chunks
     │          │
     │          ▼
     │    Relevant Context
     │          │
     ▼          ▼
OpenRouter API (Free LLM)
     │
     ▼
AI Response → User
```

## 📂 Project Structure

```
├── app/
│   ├── main.py          # FastAPI application
│   ├── chat.py          # Chat engine (OpenRouter integration)
│   └── retrieval.py     # TF-IDF RAG retrieval engine
├── scraper/
│   └── scrape.py        # DarGlobal & Wasalt web scraper
├── data/
│   ├── scraped_data.json        # Curated scraped data
│   ├── knowledge_chunks.json    # RAG text chunks (auto-generated)
│   └── raw_scraped.json         # Raw scraper output (auto-generated)
├── templates/
│   └── index.html       # Chat UI
├── static/              # Static assets
├── Dockerfile           # Multi-stage Docker build
├── docker-compose.yml   # Docker Compose configuration
├── render.yaml          # Render.com deployment config
├── requirements.txt     # Python dependencies
└── .env.example         # Environment variables template
```

## 🛠️ Local Setup

### Prerequisites
- Python 3.12+
- Docker & Docker Compose
- OpenRouter API Key (free at [openrouter.ai/keys](https://openrouter.ai/keys))

### 1. Clone & Configure

```bash
git clone <repo-url>
cd <project-folder>
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

### 2. Run with Docker (Recommended)

```bash
docker compose up --build
```

The app will be available at **http://localhost:8000**

### 3. Run Locally (Without Docker)

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Build knowledge base & start server
python run.py
```

## 🌐 Deploy to Render (Free)

1. Push code to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Set environment variable: `OPENROUTER_API_KEY=your_key`
5. Deploy! (Uses `render.yaml` config automatically)

## 🔧 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | *(required)* | Your OpenRouter API key |
| `OPENROUTER_MODEL` | `meta-llama/llama-3.1-8b-instruct:free` | Free model to use |
| `APP_URL` | `http://localhost:8000` | Public URL of the app |

### Available Free Models
- `meta-llama/llama-3.1-8b-instruct:free`
- `google/gemma-2-9b-it:free`
- `mistralai/mistral-7b-instruct:free`
- `qwen/qwen-2-7b-instruct:free`

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Chat UI |
| `/api/chat` | POST | Send a message |
| `/api/clear` | POST | Clear session history |
| `/api/health` | GET | Health check |
| `/api/info` | GET | App info & stats |

### Example API Usage

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is DarGlobal?", "session_id": "my-session"}'
```

## 📊 Data Sources

### DarGlobal (darglobal.co.uk)
- Company overview & description
- Key statistics (GDV, track record, markets)
- Financial results (FY2024, FY2025, HY2026)
- Project portfolio (AIDA, Trump International, etc.)
- Geographic presence & brand partnerships
- Recent news & press releases

### Wasalt (wasalt.com)
- Company overview & licensing
- Core services (Search, Auctions, Projects, Matchmaker, Business)
- Property types available
- Coverage cities across Saudi Arabia
- Key platform features

## 📝 License

MIT License - feel free to use and modify.
