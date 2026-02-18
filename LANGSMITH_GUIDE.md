# LangSmith Integration Guide

## 🔍 Overview

LangSmith is integrated into the chatbot for comprehensive tracing, monitoring, and debugging of all AI operations. Every interaction with the LLM is automatically traced and can be viewed in the LangSmith dashboard.

## ✅ Already Configured

The application is **pre-configured** with LangSmith tracing enabled:

```env
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=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
LANGSMITH_PROJECT=ai-product-recommendation-chatbot
```

No additional setup required! Tracing starts automatically when you run the application.

## 📊 What Gets Traced

### 1. Query Rephrasing (Step 1)
```
User Input: "I need wireless headphones with good battery"
→ LLM Rephrasing
→ Optimized Query: "wireless bluetooth headphones long battery life"
```
**Traced Data:**
- Input prompt
- LLM response
- Tokens used
- Latency
- Model: gpt-oss:20b

### 2. Vector Search (Step 3)
```
Rephrased Query
→ Embedding Generation
→ Pinecone Similarity Search
→ Retrieved Products
```
**Traced Data:**
- Search query
- Embedding model: nomic-embed-text
- Number of results
- Similarity scores
- Search latency

### 3. Web Search Fallback (Step 4)
```
No Vector Results
→ Tavily Web Search
→ Search Results
```
**Traced Data:**
- Search query
- API calls to Tavily
- Results returned
- Latency

### 4. Response Generation (Step 5)
```
Search Results + User Context
→ LLM Response Generation
→ Final User Message
```
**Traced Data:**
- Full prompt with context
- Generated response
- Tokens used
- Latency

### 5. Tool Execution (Step 4)
```
User Action (Purchase/Email)
→ Tool Invocation
→ Tool Result
```
**Traced Data:**
- Tool name
- Input parameters
- Execution result
- Success/failure status

## 🌐 Accessing LangSmith Dashboard

### Step 1: Open Dashboard
Navigate to: [https://smith.langchain.com](https://smith.langchain.com)

### Step 2: View Project
Look for project: **ai-product-recommendation-chatbot**

### Step 3: Explore Traces
Each user interaction creates a trace showing:
- Full execution timeline
- All LLM calls
- Tool invocations
- Search operations
- Latency breakdown
- Token usage
- Any errors or warnings

## 📈 Understanding Traces

### Trace Structure

```
Trace: User Query "wireless headphones"
├── Node: Rephrase Query
│   ├── LLM Call: gpt-oss:20b
│   │   ├── Input: 820 tokens
│   │   ├── Output: 45 tokens
│   │   └── Latency: 1.2s
│   └── Result: "wireless bluetooth headphones battery"
│
├── Node: User Info Retrieval
│   ├── MongoDB Query: user_001
│   └── Result: Kai He profile
│
├── Node: Vector Search
│   ├── Embedding: nomic-embed-text
│   ├── Pinecone Query
│   └── Result: 3 products found
│
└── Node: Response Generation
    ├── LLM Call: gpt-oss:20b
    │   ├── Input: 1450 tokens
    │   ├── Output: 280 tokens
    │   └── Latency: 2.3s
    └── Final Response: "I found 3 products..."
```

### Metrics Displayed

1. **Latency**
   - Total trace time
   - Per-node execution time
   - LLM inference time

2. **Token Usage**
   - Input tokens
   - Output tokens
   - Total tokens per call
   - Cumulative tokens per trace

3. **Cost Estimation**
   - Cost per LLM call (if applicable)
   - Total trace cost

4. **Success Rate**
   - Successful traces
   - Failed traces
   - Error types

## 🎯 Use Cases

### 1. Debugging Slow Responses
**Problem**: User reports slow chatbot responses

**Solution**:
1. Open LangSmith dashboard
2. Filter traces by user or time
3. Identify bottleneck:
   - Is it the LLM call? (gpt-oss:20b inference)
   - Is it vector search? (Pinecone latency)
   - Is it web search? (Tavily timeout)
4. Optimize the slow component

### 2. Improving Query Rephrasing
**Problem**: Vector search not finding relevant products

**Solution**:
1. View trace for the query
2. Compare original vs rephrased query
3. Analyze retrieved products
4. Adjust rephrasing prompt if needed
5. Test improvements in LangSmith playground

### 3. Monitoring Token Usage
**Problem**: Want to optimize costs

**Solution**:
1. View aggregated token usage
2. Identify high-token conversations
3. Optimize prompts to reduce tokens
4. Compare before/after metrics

### 4. Error Analysis
**Problem**: Some queries fail unexpectedly

**Solution**:
1. Filter traces by errors
2. View error stack traces
3. Identify common failure patterns
4. Fix issues in code

## 🔧 Advanced Configuration

### Change Project Name

Edit `backend/.env`:
```env
LANGSMITH_PROJECT=my-custom-project-name
```

### Disable Tracing

Edit `backend/.env`:
```env
LANGSMITH_TRACING=false
```

### Add Custom Metadata

In `backend/app/agents/graph.py`:
```python
from langsmith import traceable

@traceable(name="custom_step", metadata={"version": "1.0"})
async def custom_node(state: GraphState) -> GraphState:
    # Your code here
    return state
```

### Filter Traces

Add tags in your code:
```python
from langsmith import traceable

@traceable(tags=["production", "high-priority"])
async def important_function():
    pass
```

## 📊 Example Traces

### Successful Product Search

```
Trace ID: tr_abc123
Duration: 4.2s
Status: ✅ Success
Tokens: 2,145 (input: 1,820 | output: 325)

Timeline:
0.0s  → Query received: "wireless headphones"
0.1s  → Rephrase started
1.3s  → Rephrase complete
1.3s  → User retrieval: Kai He
1.4s  → Vector search started
2.1s  → Found 3 products
2.1s  → Response generation started
4.2s  → Response complete
```

### Failed Search with Web Fallback

```
Trace ID: tr_xyz789
Duration: 8.5s
Status: ✅ Success (with fallback)
Tokens: 3,421 (input: 2,980 | output: 441)

Timeline:
0.0s  → Query received: "quantum processors"
0.1s  → Rephrase started
1.5s  → Rephrase complete
1.5s  → Vector search started
2.2s  → No products found ⚠️
2.2s  → Web search fallback triggered
5.8s  → Tavily results: 5 articles
5.8s  → Response generation started
8.5s  → Response complete
```

## 🛠️ Troubleshooting

### Traces Not Appearing

**Check 1**: Verify API key
```bash
grep LANGSMITH_API_KEY backend/.env
```

**Check 2**: Verify tracing is enabled
```bash
grep LANGSMITH_TRACING backend/.env
# Should show: LANGSMITH_TRACING=true
```

**Check 3**: Check logs
```bash
docker-compose logs backend | grep LangSmith
# Should see: "LangSmith tracing enabled"
```

### Traces Missing Details

**Issue**: Traces appear but lack detail

**Solution**: Ensure all nodes use LangChain components:
- Use `ChatOllama` instead of raw Ollama calls
- Use LangChain's `TavilySearchResults` for web search
- All database operations should be wrapped in traceable functions

### High Latency Traces

**Issue**: Traces show high latency

**Possible Causes**:
1. **gpt-oss:20b Model**: 20B model is slow on CPU
   - Solution: Use GPU or smaller model (mistral, llama2)

2. **Cold Start**: First request loads model
   - Solution: Keep Ollama warm with periodic requests

3. **Vector Search**: Large index or slow connection
   - Solution: Optimize Pinecone index, check network

4. **Prompt Size**: Very long prompts
   - Solution: Reduce context window, summarize history

## 📚 Best Practices

### 1. Tag Your Traces
```python
@traceable(tags=["user:kai_he", "feature:search"])
async def search_products(query: str):
    pass
```

### 2. Add Metadata
```python
@traceable(metadata={"user_id": "user_001", "source": "mobile_app"})
async def process_query(query: str):
    pass
```

### 3. Monitor Regularly
- Check dashboard daily
- Set up alerts for errors
- Review slow traces weekly
- Analyze token usage monthly

### 4. Use Feedback
LangSmith allows user feedback on traces:
- Add thumbs up/down in your UI
- Send feedback via LangSmith API
- Improve based on feedback data

## 🔐 Security Notes

- API key is included in `.env.example` for this demo
- In production, use environment-specific keys
- Rotate keys regularly
- Use separate projects for dev/staging/prod
- Review trace data retention policies

## 📖 Additional Resources

- **LangSmith Docs**: [https://docs.smith.langchain.com](https://docs.smith.langchain.com)
- **Python SDK**: [https://github.com/langchain-ai/langsmith-sdk](https://github.com/langchain-ai/langsmith-sdk)
- **Tracing Guide**: [https://docs.smith.langchain.com/tracing](https://docs.smith.langchain.com/tracing)

## 🎉 Summary

✅ LangSmith is pre-configured and ready to use
✅ All AI operations are automatically traced
✅ View detailed execution flows in dashboard
✅ Monitor performance and optimize bottlenecks
✅ Debug issues with full context
✅ Analyze token usage and costs

Start using the chatbot and watch the traces appear in real-time at [smith.langchain.com](https://smith.langchain.com)!
