# Product Recommendation Chatbot

A production-ready AI-powered chatbot application that recommends products based on user needs using RAG (Retrieval-Augmented Generation) architecture with LangGraph for workflow orchestration.

## 🚀 Features

- **Intelligent Product Search**: Uses vector similarity search with Pinecone and semantic understanding
- **Query Rephrasing**: Automatically optimizes user queries for better search results
- **User Management**: MongoDB-based user profile storage and retrieval
- **Web Search Fallback**: Tavily integration for when products aren't in the database
- **Action Tools**: Purchase and email product details functionality
- **Conversational AI**: Natural language interaction powered by Ollama
- **Modern UI**: Responsive React interface with Tailwind CSS
- **Production-Ready**: Docker-based deployment, comprehensive logging, error handling

## 📋 Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **AI/LLM**: LangChain, Ollama
- **Monitoring**: LangSmith (for tracing and debugging)
- **Vector Database**: Pinecone
- **Database**: MongoDB
- **Web Search**: Tavily API
- **Package Manager**: UV (ultra-fast Python package manager)

### Frontend
- **Framework**: React 18+
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios
- **Icons**: Lucide React

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Reverse Proxy**: Nginx

## 🏗️ Architecture

```
┌─────────────┐
│   React UI  │
└──────┬──────┘
       │ HTTP/REST
       ▼
┌─────────────────────────────────────┐
│         FastAPI Backend             │
│  ┌───────────────────────────────┐  │
│  │   LangChain Workflow Service  │  │
│  │  ├─ Query Rephrase Chain      │  │
│  │  ├─ User Info Retrieval       │  │
│  │  ├─ Vector Search              │  │
│  │  ├─ Web Search Fallback        │  │
│  │  ├─ Action Execution           │  │
│  │  └─ Response Generation Chain │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
       │         │         │
       ▼         ▼         ▼
   ┌────────┐ ┌──────┐ ┌───────┐
   │Pinecone│ │MongoDB│ │Tavily │
   └────────┘ └──────┘ └───────┘
```

## 🚦 Prerequisites

- Docker & Docker Compose
- **Ollama installed locally** with models: `gpt-oss:20b` and `nomic-embed-text`
- Pinecone API key (free tier available)
- Tavily API key (optional, for web search)
- SMTP credentials (optional, for email functionality)

## 📦 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd product-recommendation-chatbot
```

### 2. Set Up Environment Variables

**Backend (.env)**:
```bash
cd backend
cp .env.example .env
# Edit .env with your credentials
```

**Frontend (.env)**:
```bash
cd ../frontend
cp .env.example .env
# Edit if needed
```

### 3. Configure API Keys

Edit `backend/.env`:
```bash
# Pinecone (Required)
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENVIRONMENT=gcp-starter

# Tavily (Optional - for web search)
TAVILY_API_KEY=your_tavily_api_key_here

# SMTP (Optional - for email functionality)
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password_here
```

## 🏃 Running the Application

### Ensure Ollama is Running Locally

```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags

# Pull required models if not already available
ollama pull gpt-oss:20b
ollama pull nomic-embed-text

# Verify models
ollama list
```

### Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Setup

**1. Start MongoDB**:
```bash
docker run -d -p 27017:27017 --name mongodb mongo:7
```

**2. Verify Ollama**:
```bash
# Make sure Ollama is running locally
ollama list
ollama pull gpt-oss:20b
ollama pull nomic-embed-text
```

**3. Start Backend**:
```bash
cd backend
uv pip install -r pyproject.toml
python -m app.main
```

**4. Start Frontend**:
```bash
cd frontend
npm install
npm run dev
```

## 📊 Database Initialization

### 1. Initialize Users

```bash
cd backend
python scripts/init_db.py
```

This creates three sample users:
- `user_001`: Kai He (kai.he@example.com)
- `user_002`: Jane Smith (jane.smith@example.com)
- `user_003`: Bob Johnson (bob.johnson@example.com)

### 2. Load Product Data

```bash
python scripts/load_products.py
```

This loads sample products from `backend/data/products/*.json` into Pinecone.

## 🧪 Testing

### Test Backend API

```bash
# Health check
curl http://localhost:8000/health

# Create user
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "test_user",
    "firstName": "Test",
    "lastName": "User",
    "email": "test@example.com",
    "phone": "+1234567890"
  }'

# Chat request
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-User-ID: user_001" \
  -d '{
    "query": "I need wireless headphones with good battery life"
  }'
```

### Run Unit Tests

```bash
cd backend
pytest tests/
```

## 📝 API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### POST `/api/v1/chat`
Chat with the assistant for product recommendations.

**Headers**:
- `X-User-ID`: User identifier (required)

**Request Body**:
```json
{
  "query": "I need wireless headphones",
  "conversation_id": "optional-conv-id"
}
```

**Response**:
```json
{
  "message": "I found 3 products...",
  "products": [...],
  "conversation_id": "conv-123",
  "has_results": true,
  "source": "vector_db"
}
```

#### POST `/api/v1/actions`
Execute purchase or email action.

**Headers**:
- `X-User-ID`: User identifier (required)

**Request Body**:
```json
{
  "action": "email",
  "product_id": "prod_001",
  "conversation_id": "conv-123"
}
```

## 🎨 Frontend Usage

1. **Open Application**: Navigate to http://localhost:3000
2. **Select User**: Choose from dropdown (John Doe, Jane Smith, Bob Johnson)
3. **Enter Query**: Type what you're looking for
4. **View Results**: Browse recommended products
5. **Take Action**: Click "Purchase" or email icon to proceed

## 🔧 Configuration

### LangSmith Tracing

LangSmith is integrated for monitoring and debugging AI workflows. View traces at [smith.langchain.com](https://smith.langchain.com).

**Enable in `backend/.env`:**
```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=ai-product-recommendation-chatbot
```

**What gets traced:**
- Query rephrasing steps
- Vector search operations
- LLM reasoning chains
- Tool execution (purchase/email)
- Web search fallbacks
- Response generation

View detailed traces, costs, and latency metrics in the LangSmith dashboard.

### Ollama Models

Download additional models to your local Ollama:
```bash
ollama pull mistral
ollama pull mixtral
ollama list
```

Update `backend/.env`:
```bash
OLLAMA_MODEL=mistral
```

### Vector Search Tuning

Adjust search parameters in `backend/.env`:
```bash
VECTOR_SEARCH_THRESHOLD=0.7  # Similarity threshold (0-1)
VECTOR_SEARCH_TOP_K=5        # Number of results
```

### Rate Limiting

Configure in `backend/.env`:
```bash
RATE_LIMIT_REQUESTS=10  # Requests per period
RATE_LIMIT_PERIOD=60    # Period in seconds
```

## 📁 Project Structure

```
product-recommendation-chatbot/
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph workflow
│   │   ├── api/             # FastAPI routes
│   │   ├── database/        # DB connections
│   │   ├── models/          # Pydantic models
│   │   ├── services/        # Business logic
│   │   └── utils/           # Utilities
│   ├── data/products/       # Sample JSON data
│   ├── scripts/             # Initialization scripts
│   └── tests/               # Unit tests
├── frontend/
│   └── src/
│       ├── components/      # React components
│       ├── hooks/           # Custom hooks
│       └── services/        # API client
└── docker-compose.yml       # Orchestration
```

## 🐛 Troubleshooting

### Ollama Connection Issues

```bash
# Check if Ollama is running locally
curl http://localhost:11434/api/tags

# Verify models are installed
ollama list

# Pull required models
ollama pull gpt-oss:20b
ollama pull nomic-embed-text

# If running backend in Docker, ensure host.docker.internal is accessible
# On Linux, you may need to use --add-host=host.docker.internal:host-gateway
```

### Pinecone Connection Issues

- Verify API key in `.env`
- Check index name matches configuration
- Ensure dimension matches embedding model (384 for nomic-embed-text)

### MongoDB Connection Issues

```bash
# Check MongoDB status
docker exec -it mongodb mongosh

# List databases
show dbs

# Check collections
use product_chatbot
show collections
```

## 🔐 Security Considerations

- **API Keys**: Never commit `.env` files
- **CORS**: Configure `CORS_ORIGINS` for production
- **Rate Limiting**: Enabled by default
- **Input Validation**: All inputs validated with Pydantic
- **HTTPS**: Use reverse proxy (nginx/Traefik) in production

## 📈 Performance Optimization

- **Connection Pooling**: MongoDB and HTTP clients use connection pools
- **Caching**: Vector search results can be cached (implement Redis)
- **Async**: All I/O operations are async
- **Batch Processing**: Load products in batches

## 🚀 Deployment

### Production Checklist

- [ ] Update `ENVIRONMENT=production` in `.env`
- [ ] Set `DEBUG=false`
- [ ] Configure production CORS origins
- [ ] Use production database URLs
- [ ] Enable HTTPS
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure log aggregation (ELK/Loki)
- [ ] Set up backup strategy for MongoDB

### Kubernetes Deployment

See `k8s/` directory for Kubernetes manifests (create if needed).

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📧 Support

For issues and questions:
- Open a GitHub issue
- Check existing documentation
- Review API documentation at `/docs`

## 🙏 Acknowledgments

- LangChain & LangGraph teams
- Anthropic for Claude
- Pinecone for vector database
- FastAPI community
- React community
