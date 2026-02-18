# AI Product Recommendation Chatbot - Project Plan

## Executive Summary
A production-ready AI chatbot application that suggests products based on user needs using RAG (Retrieval-Augmented Generation) architecture with LangGraph for workflow orchestration.

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **AI/LLM**: LangChain/LangGraph, Ollama (local LLM)
- **Vector Database**: Pinecone
- **Database**: MongoDB
- **Web Search**: Tavily API
- **Package Manager**: UV (ultra-fast Python package manager)
- **Containerization**: Docker & Docker Compose

### Frontend
- **Framework**: React 18+
- **Build Tool**: Vite
- **HTTP Client**: Axios
- **UI Library**: Tailwind CSS

## Architecture Overview

```
┌─────────────┐
│   React UI  │
└──────┬──────┘
       │ HTTP/REST
       ▼
┌─────────────────────────────────────┐
│         FastAPI Backend             │
│  ┌───────────────────────────────┐  │
│  │   LangGraph Workflow Engine   │  │
│  │  ├─ Query Rephrase Node       │  │
│  │  ├─ User Info Retrieval Node  │  │
│  │  ├─ Vector Search Node        │  │
│  │  ├─ Web Search Fallback Node  │  │
│  │  ├─ Tool Execution Node       │  │
│  │  └─ Response Generation Node  │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
       │         │         │
       ▼         ▼         ▼
   ┌────────┐ ┌──────┐ ┌───────┐
   │Pinecone│ │MongoDB│ │Tavily │
   └────────┘ └──────┘ └───────┘
```

## Project Structure

```
product-recommendation-chatbot/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application entry
│   │   ├── config.py               # Configuration management
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py            # User data models
│   │   │   ├── product.py         # Product data models
│   │   │   └── request.py         # API request/response models
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── mongodb.py         # MongoDB connection
│   │   │   └── pinecone_db.py     # Pinecone vector store
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── data_loader.py     # JSON data loader
│   │   │   ├── user_service.py    # User CRUD operations
│   │   │   └── email_service.py   # Email sending service
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── graph.py           # LangGraph workflow
│   │   │   ├── nodes.py           # Graph nodes
│   │   │   ├── tools.py           # LangChain tools
│   │   │   └── state.py           # Graph state management
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py          # API endpoints
│   │   │   └── middleware.py      # Custom middleware
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── logger.py          # Logging configuration
│   │       └── helpers.py         # Utility functions
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_api.py
│   │   ├── test_services.py
│   │   └── test_agents.py
│   ├── data/
│   │   └── products/              # Sample JSON product files
│   ├── scripts/
│   │   ├── init_db.py            # Database initialization
│   │   └── load_products.py      # Product data loader
│   ├── pyproject.toml            # UV project file
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface.jsx
│   │   │   ├── MessageList.jsx
│   │   │   ├── InputBox.jsx
│   │   │   └── ProductCard.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── hooks/
│   │   │   └── useChat.js
│   │   ├── utils/
│   │   │   └── helpers.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.js
│   ├── Dockerfile
│   └── .env.example
├── docker-compose.yml
├── .env.example
├── README.md
└── .gitignore
```

## Detailed Workflow Implementation

### Step 1: Query Rephrasing
- Use Ollama LLM with prompt engineering
- Convert user's natural language to optimized search query
- Preserve intent while improving retrieval quality

### Step 2: User Information Retrieval
- Extract userId from request header
- Query MongoDB for user profile
- Cache user data in graph state

### Step 3: Vector Search with Fallback
- Query Pinecone with rephrased query
- Similarity threshold: 0.7
- If no results: Fallback to Tavily web search
- Return top 5 products

### Step 4: Tool Execution
- **Purchase Tool**: Process order, update inventory
- **Email Tool**: Send product details via email
- Tools implemented as LangChain tools with proper error handling

### Step 5: Action Confirmation
- Return structured response
- Include action status and details

### Step 6: Follow-up Prompt
- Ask if user needs further assistance
- Maintain conversation context

### Step 7: UI Implementation
- Real-time chat interface
- Product cards with images
- Action buttons (Purchase/Email)
- Loading states and error handling

## Data Models

### Product Schema (JSON)
```json
{
  "product_id": "string",
  "name": "string",
  "description": "string",
  "category": "string",
  "price": "number",
  "specifications": "object",
  "image_url": "string",
  "stock": "number",
  "tags": ["array"]
}
```

### User Schema (MongoDB)
```json
{
  "userId": "string",
  "firstName": "string",
  "lastName": "string",
  "email": "string",
  "phone": "string",
  "createdAt": "datetime",
  "updatedAt": "datetime"
}
```

## Security Considerations

1. **API Security**
   - Rate limiting (10 req/min per user)
   - Request validation with Pydantic
   - CORS configuration
   - API key authentication

2. **Data Security**
   - Environment variable management
   - MongoDB connection encryption
   - Input sanitization
   - PII data protection

3. **Error Handling**
   - Graceful degradation
   - Detailed logging
   - User-friendly error messages

## Monitoring & Logging

- Structured logging with Python's logging module
- Request/Response logging
- Error tracking
- Performance metrics

## Deployment Strategy

1. **Development**: Docker Compose (all services local)
2. **Staging**: Kubernetes cluster
3. **Production**: Cloud deployment (AWS/GCP/Azure)

## Testing Strategy

1. **Unit Tests**: pytest for individual functions
2. **Integration Tests**: API endpoint testing
3. **E2E Tests**: Full workflow validation
4. **Load Tests**: Performance benchmarking

## Performance Optimization

1. **Backend**
   - Connection pooling (MongoDB)
   - Vector search caching
   - Async/await patterns
   - Response compression

2. **Frontend**
   - Code splitting
   - Lazy loading
   - Memoization
   - Bundle optimization

## Scalability Considerations

- Horizontal scaling with Docker/Kubernetes
- Redis caching layer (future enhancement)
- Message queue for async tasks (Celery)
- Load balancing

## Development Timeline

- **Phase 1** (Week 1): Backend core + Database setup
- **Phase 2** (Week 2): LangGraph workflow implementation
- **Phase 3** (Week 3): API endpoints + Testing
- **Phase 4** (Week 4): Frontend development
- **Phase 5** (Week 5): Integration + Deployment

## Next Steps

1. Set up development environment
2. Initialize UV project
3. Configure Docker Compose
4. Implement core backend services
5. Build LangGraph workflow
6. Create API endpoints
7. Develop React frontend
8. Write tests
9. Documentation
10. Deploy to staging
