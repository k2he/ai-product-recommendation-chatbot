# Custom Setup Guide - Local Ollama with gpt-oss:20b

## ✨ Your Configuration

- **Ollama**: Running locally (not in Docker)
- **Model**: gpt-oss:20b
- **Primary User**: Kai He (user_001)

## 🚀 Quick Setup

### Step 1: Verify Local Ollama

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Should return JSON with available models
```

### Step 2: Pull Required Models

```bash
# Pull the gpt-oss:20b model
ollama pull gpt-oss:20b

# Pull the embedding model
ollama pull nomic-embed-text

# Verify both models are available
ollama list
# Should show:
# - gpt-oss:20b
# - nomic-embed-text
```

### Step 3: Configure Backend

```bash
cd backend

# Copy environment template
cp .env.example .env

# Edit .env file
nano .env  # or use your preferred editor
```

**Key settings in .env:**
```env
# Ollama - Points to your local installation
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gpt-oss:20b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Pinecone (Already configured)
PINECONE_API_KEY=pcsk_2dNYb5_M9shvZveRciF8m249T5cw56YMvSYNgnEtVGXMgfZdTVJSQzekgxu46pUJrKFcG9

# Tavily (Already configured)
TAVILY_API_KEY=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

# LangSmith (Already configured - for tracing)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=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
LANGSMITH_PROJECT=ai-product-recommendation-chatbot
```

### Step 4: Start Services

```bash
# From project root
cd ..

# Start MongoDB, Backend, and Frontend
docker-compose up -d

# Check all services are running
docker-compose ps
```

### Step 5: Initialize Database

```bash
# Create sample users (includes Kai He as user_001)
docker exec -it product_chatbot_backend python scripts/init_db.py

# Load product data into Pinecone
docker exec -it product_chatbot_backend python scripts/load_products.py
# When prompted, enter 'y' to clear existing data
```

### Step 6: Access Application

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🎯 Testing Your Setup

### Test 1: Check Ollama Connection

```bash
# Test from your host
curl http://localhost:11434/api/generate -d '{
  "model": "gpt-oss:20b",
  "prompt": "Hello, test",
  "stream": false
}'
```

### Test 2: Check Backend Can Reach Ollama

```bash
# View backend logs
docker-compose logs backend

# Should see: "Connected to Ollama" or similar
```

### Test 3: Use the Chat Interface

1. Open http://localhost:3000
2. Select "Kai He" from the dropdown
3. Enter a query: "I need wireless headphones with good battery life"
4. You should see:
   - Query being rephrased by gpt-oss:20b
   - Product recommendations
   - Options to purchase or email

## 🐛 Troubleshooting

### Issue: Backend Can't Connect to Ollama

**Symptom**: "Connection refused" or "Ollama not available" errors

**Solution**:
```bash
# 1. Verify Ollama is running on host
curl http://localhost:11434/api/tags

# 2. Check Docker can reach host
docker exec -it product_chatbot_backend curl http://host.docker.internal:11434/api/tags

# 3. On Linux, you may need to update docker-compose.yml
# Change OLLAMA_BASE_URL to use your actual IP:
# OLLAMA_BASE_URL=http://192.168.1.x:11434
```

### Issue: Model Not Found

**Symptom**: "model 'gpt-oss:20b' not found"

**Solution**:
```bash
# Pull the model
ollama pull gpt-oss:20b

# Verify it's available
ollama list | grep gpt-oss
```

### Issue: Slow Response Times

**Symptom**: Chat responses take a long time

**Possible Causes**:
- gpt-oss:20b is a 20B parameter model and may be slow on CPU
- First request is slower (model loading)
- Consider using a smaller model for faster responses

**Solutions**:
```bash
# Option 1: Use a smaller model
ollama pull mistral
# Update backend/.env: OLLAMA_MODEL=mistral

# Option 2: Keep model loaded
ollama run gpt-oss:20b
# Keep this terminal open to keep model in memory
```

### Issue: Out of Memory

**Symptom**: Ollama crashes or backend shows memory errors

**Solution**:
```bash
# gpt-oss:20b requires significant RAM (16GB+ recommended)
# Use a smaller model if needed:
ollama pull mistral  # ~4GB RAM
ollama pull llama2   # ~4-8GB RAM

# Update .env
OLLAMA_MODEL=mistral
```

## 🔧 Running Frontend Separately

If you want to run the frontend outside Docker:

```bash
# Terminal 1: Keep backend in Docker
docker-compose up backend mongodb

# Terminal 2: Run frontend locally
cd frontend
npm install
npm run dev

# Access at http://localhost:5173
```

## 📊 Your User Setup

The database is initialized with:

**Primary User (user_001)**:
- Name: Kai He
- Email: kai.he@example.com
- Phone: +1234567890

**Other Users**:
- user_002: Jane Smith
- user_003: Bob Johnson

Select "Kai He" in the UI dropdown to use your primary account.

## ⚙️ Advanced Configuration

### Adjust Model Temperature

Edit `backend/.env`:
```env
OLLAMA_TEMPERATURE=0.7  # Default
# Lower (0.3) = more focused, deterministic
# Higher (0.9) = more creative, varied
```

### Adjust Token Limit

```env
OLLAMA_MAX_TOKENS=2000  # Default
# Increase for longer responses
# Decrease for faster responses
```

### Change Embedding Model

```env
OLLAMA_EMBEDDING_MODEL=nomic-embed-text  # Recommended
# Or use: all-minilm, bge-large, etc.
```

## 🎨 Frontend Customization

The UI displays "Kai He" as the first user option. To customize:

Edit `frontend/src/components/ChatInterface.jsx`:
```javascript
<option value="user_001">Kai He</option>
```

## 📝 Sample Queries to Test

Try these with gpt-oss:20b:

1. **Product Search**:
   - "I need wireless headphones with good battery life"
   - "Show me ergonomic office chairs under $400"
   - "Looking for a 4K webcam for remote work"

2. **Specific Requirements**:
   - "I want noise-cancelling earbuds that are waterproof"
   - "Find me a standing desk converter with a large surface"
   - "Show me smart home security cameras with cloud storage"

3. **Action Testing**:
   - After seeing products, click "Purchase" to test order flow
   - Click email icon to test email functionality

## 🚀 Next Steps

1. ✅ Verify Ollama connection
2. ✅ Test chat with gpt-oss:20b
3. ✅ Add your own products to `backend/data/products/`
4. ✅ Customize UI colors/branding
5. ✅ Set up email SMTP for actual email sending
6. ✅ Deploy to production when ready

## 📞 Need Help?

- Check main README.md for comprehensive docs
- View API documentation at http://localhost:8000/docs
- Check logs: `docker-compose logs -f backend`
- Test Ollama: `curl http://localhost:11434/api/tags`

Your setup is optimized for local Ollama with the powerful gpt-oss:20b model! 🎉
