# Quick Start Guide

## ⚡ Get Started in 5 Minutes

### Step 1: Prerequisites
```bash
# Install Docker and Docker Compose
# Verify installation
docker --version
docker-compose --version
```

### Step 2: Get API Keys

1. **Pinecone** (Required): https://www.pinecone.io/
   - Sign up for free account
   - Create a new index or use existing
   - Copy API key

2. **Tavily** (Optional): https://tavily.com/
   - Sign up for API key
   - Free tier available

### Step 3: Configure Environment

```bash
# Navigate to backend directory
cd backend

# Copy example env file
cp .env.example .env

# The following are already configured:
# ✅ Pinecone API key
# ✅ Tavily API key  
# ✅ LangSmith tracing
# ✅ gpt-oss:20b model

# Optional: Add SMTP credentials for email functionality
nano .env  # or use your preferred editor
```

### Step 4: Start Services

```bash
# From project root directory
cd ..

# Start all services
docker-compose up -d

# Wait for services to be healthy (2-3 minutes)
docker-compose ps
```

### Step 5: Verify Local Ollama

```bash
# Make sure your local Ollama is running
ollama list

# Ensure you have the required models
ollama pull gpt-oss:20b
ollama pull nomic-embed-text

# Test that Ollama is accessible
curl http://localhost:11434/api/tags
```

### Step 6: Initialize Database

```bash
# Initialize users
docker exec -it product_chatbot_backend python scripts/init_db.py

# Load product data
docker exec -it product_chatbot_backend python scripts/load_products.py
# When prompted, enter 'y' to clear existing data
```

### Step 7: Access Application

Open your browser and navigate to:
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

### Step 8: Test the Chatbot

1. Select a user from dropdown (John Doe, Jane Smith, or Bob Johnson)
2. Enter a query like:
   - "I need wireless headphones with good battery life"
   - "Show me ergonomic office chairs"
   - "Looking for a 4K webcam for video calls"
3. View recommended products
4. Click "Purchase" or email icon to test actions

## 🔍 Verify Installation

```bash
# Check all services are running
docker-compose ps

# Should show:
# - product_chatbot_mongodb (healthy)
# - product_chatbot_backend (healthy)
# - product_chatbot_frontend (healthy)

# Check backend health
curl http://localhost:8000/health

# Check frontend
curl http://localhost:3000
```

## 🐛 Common Issues

### Issue: Ollama models not found
```bash
# Solution: Pull models to your local Ollama
ollama pull gpt-oss:20b
ollama pull nomic-embed-text

# Verify models are available
ollama list
```

### Issue: Cannot connect to Ollama
```bash
# Solution: Ensure local Ollama is running
# Check Ollama status
curl http://localhost:11434/api/tags

# If not running, start Ollama service
# On Mac: Ollama should be running from Applications
# On Linux: systemctl start ollama
# On Windows: Start Ollama from Start menu
```

### Issue: Pinecone connection error
```bash
# Solution: Verify API key and environment
# Check backend/.env file
# Ensure PINECONE_API_KEY is correct
```

### Issue: No products found
```bash
# Solution: Load product data
docker exec -it product_chatbot_backend python scripts/load_products.py
```

### Issue: User not found
```bash
# Solution: Initialize database
docker exec -it product_chatbot_backend python scripts/init_db.py
```

## 📚 Next Steps

- Read full [README.md](README.md) for detailed documentation
- Add custom products in `backend/data/products/`
- Customize frontend UI
- Configure email settings for email functionality
- Explore API documentation at http://localhost:8000/docs

## 💡 Sample Queries

Try these queries to test the chatbot:
- "I need a standing desk converter under $350"
- "Show me wireless earbuds with noise cancellation"
- "Looking for ergonomic office furniture"
- "Best webcam for video conferencing"
- "Smart home security cameras with cloud storage"

## 🛑 Stop Services

```bash
# Stop all services
docker-compose down

# Remove volumes (database data)
docker-compose down -v
```

## 📞 Need Help?

- Check [README.md](README.md) for detailed documentation
- Review API docs at http://localhost:8000/docs
- Check docker logs: `docker-compose logs -f`
