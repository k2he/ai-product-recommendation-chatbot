# LangChain Implementation Guide

## 🔄 Architecture Change: LangGraph → LangChain

This project has been updated to use **LangChain** with sequential chains instead of **LangGraph**. This provides a simpler, more straightforward implementation while maintaining all functionality.

## 🎯 Why LangChain Instead of LangGraph?

### LangGraph (Previous)
- Graph-based workflow with nodes and edges
- More complex state management
- Better for cyclical workflows and dynamic routing
- Requires understanding of graph concepts

### LangChain (Current)
- Sequential chain-based workflow
- Simpler linear execution
- Better for straightforward pipelines
- Easier to understand and maintain
- Still supports conditional logic

## 📋 Implementation Overview

### Core Component: `ChatbotService`

Located at: `backend/app/services/chatbot_service.py`

```python
class ChatbotService:
    """LangChain-based chatbot service."""
    
    def __init__(self):
        # Initialize LLM
        self.llm = ChatOllama(...)
        
        # Initialize search tools
        self.tavily = TavilySearchResults(...)
        
        # Build chains
        self._build_chains()
```

## 🔗 LangChain Chains

### Chain 1: Query Rephrasing Chain

**Purpose**: Optimize user's natural language query for vector search

**Implementation**:
```python
rephrase_prompt = PromptTemplate(
    input_variables=["query"],
    template="Rephrase this query for semantic search: {query}"
)

self.rephrase_chain = LLMChain(
    llm=self.llm,
    prompt=rephrase_prompt,
    output_key="rephrased_query"
)
```

**Usage**:
```python
rephrased_query = await self.rephrase_chain.arun(query=user_query)
```

### Chain 2: Response Generation Chain

**Purpose**: Generate user-friendly responses from search results

**Implementation**:
```python
response_prompt = PromptTemplate(
    input_variables=["user_name", "products", "has_results", "source"],
    template="Generate response for user {user_name}..."
)

self.response_chain = LLMChain(
    llm=self.llm,
    prompt=response_prompt,
    output_key="final_response"
)
```

**Usage**:
```python
response = await self.response_chain.arun(
    user_name=user_name,
    products=product_list,
    has_results=True,
    source="vector_db"
)
```

## 🔄 Workflow Steps

### Step-by-Step Execution

```python
async def execute_query(self, user_query, user_id, conversation_id):
    # Step 1: Rephrase Query
    rephrased_query = await self.rephrase_chain.arun(query=user_query)
    
    # Step 2: Get User Info
    user_info = await self._get_user_info(user_id)
    
    # Step 3: Vector Search
    products = await self._search_products(rephrased_query)
    
    # Step 4: Web Search Fallback (if needed)
    if not products:
        web_results = await self._web_search(rephrased_query)
    
    # Step 5: Generate Response
    response = await self._generate_response(user_name, products)
    
    return {
        "message": response,
        "products": products,
        ...
    }
```

## 📊 Workflow Diagram

```
User Query
    ↓
┌─────────────────────┐
│ Rephrase Chain      │ ← LangChain LLMChain
│ (gpt-oss:20b)       │
└─────────────────────┘
    ↓
Query: "wireless bluetooth headphones battery"
    ↓
┌─────────────────────┐
│ User Retrieval      │ ← MongoDB
│ (user_001: Kai He)  │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ Vector Search       │ ← Pinecone + nomic-embed-text
│ (3 products found)  │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ Response Chain      │ ← LangChain LLMChain
│ (gpt-oss:20b)       │
└─────────────────────┘
    ↓
Response to User
```

## 🛠️ Key Methods

### 1. Query Execution

```python
await chatbot_service.execute_query(
    user_query="I need wireless headphones",
    user_id="user_001",
    conversation_id="conv_123"
)
```

Returns:
```python
{
    "message": "Hello Kai! I found 3 products...",
    "products": [Product, Product, Product],
    "conversation_id": "conv_123",
    "has_results": True,
    "source": "vector_db",
    "error": None
}
```

### 2. Action Execution

```python
await chatbot_service.execute_action(
    action=ActionType.EMAIL,
    product_id="prod_001",
    user_id="user_001"
)
```

Returns:
```python
{
    "success": True,
    "message": "Product details sent to kai.he@example.com",
    "action": "email",
    "product_id": "prod_001",
    "details": {...}
}
```

## 🔍 Comparison: LangGraph vs LangChain

### LangGraph Version (Previous)

```python
# Define nodes
workflow.add_node("rephrase_query", rephrase_query_node)
workflow.add_node("retrieve_user", retrieve_user_node)
workflow.add_node("vector_search", vector_search_node)

# Define edges
workflow.add_edge("rephrase_query", "retrieve_user")
workflow.add_edge("retrieve_user", "vector_search")

# Conditional edges
workflow.add_conditional_edges(
    "vector_search",
    should_continue_to_web_search,
    {"web_search": "web_search", "generate": "generate_response"}
)

# Execute
result = await graph.ainvoke(state)
```

### LangChain Version (Current)

```python
# Define chains
rephrase_chain = LLMChain(llm=llm, prompt=rephrase_prompt)
response_chain = LLMChain(llm=llm, prompt=response_prompt)

# Execute sequentially
rephrased = await rephrase_chain.arun(query=query)
user_info = await get_user(user_id)
products = await search_products(rephrased)

if not products:
    web_results = await web_search(rephrased)
    
response = await response_chain.arun(
    user_name=user_info.firstName,
    products=products
)
```

**Advantages**:
- ✅ Simpler to understand
- ✅ Easier to debug
- ✅ More explicit control flow
- ✅ Less boilerplate code
- ✅ Same functionality

## 🎯 LangSmith Tracing

LangSmith still works perfectly with LangChain chains!

### What Gets Traced

1. **Rephrase Chain Execution**
   - Input: User query
   - LLM call to gpt-oss:20b
   - Output: Rephrased query
   - Tokens and latency

2. **Response Chain Execution**
   - Input: User info + Products
   - LLM call to gpt-oss:20b
   - Output: Generated response
   - Tokens and latency

3. **Tool Invocations**
   - Vector search operations
   - Web search calls
   - Database queries

### Example Trace

```
Trace: "wireless headphones"
├─ LLMChain: rephrase_chain
│  ├─ Input: 820 tokens
│  ├─ LLM: gpt-oss:20b (1.2s)
│  └─ Output: 45 tokens
│
├─ MongoDB: get_user (0.1s)
├─ Pinecone: search_products (0.8s)
│
└─ LLMChain: response_chain
   ├─ Input: 1,450 tokens
   ├─ LLM: gpt-oss:20b (2.1s)
   └─ Output: 280 tokens

Total: 4.2s | 2,595 tokens
```

## 📝 Code Examples

### Creating Custom Chains

```python
# Custom chain for product comparison
comparison_prompt = PromptTemplate(
    input_variables=["product1", "product2"],
    template="""
    Compare these two products:
    Product 1: {product1}
    Product 2: {product2}
    
    Provide a detailed comparison:
    """
)

comparison_chain = LLMChain(
    llm=self.llm,
    prompt=comparison_prompt
)

result = await comparison_chain.arun(
    product1="Product A details",
    product2="Product B details"
)
```

### Sequential Chains

```python
from langchain.chains import SequentialChain

# Chain 1: Extract features
extract_chain = LLMChain(
    llm=llm,
    prompt=extract_prompt,
    output_key="features"
)

# Chain 2: Search based on features
search_chain = LLMChain(
    llm=llm,
    prompt=search_prompt,
    output_key="search_query"
)

# Combine them
full_chain = SequentialChain(
    chains=[extract_chain, search_chain],
    input_variables=["user_input"],
    output_variables=["features", "search_query"]
)

result = await full_chain.arun(user_input="I need a laptop")
```

## 🔧 Customization

### Adding New Chains

1. **Define the prompt**:
```python
new_prompt = PromptTemplate(
    input_variables=["input_var"],
    template="Your template here: {input_var}"
)
```

2. **Create the chain**:
```python
new_chain = LLMChain(
    llm=self.llm,
    prompt=new_prompt,
    output_key="output_var"
)
```

3. **Use in workflow**:
```python
result = await new_chain.arun(input_var="value")
```

### Modifying Existing Chains

Edit `backend/app/services/chatbot_service.py`:

```python
def _build_chains(self):
    # Modify rephrase prompt
    rephrase_prompt = PromptTemplate(
        input_variables=["query"],
        template="""
        Your custom template here.
        Focus on: {query}
        """
    )
    
    self.rephrase_chain = LLMChain(
        llm=self.llm,
        prompt=rephrase_prompt
    )
```

## 🐛 Debugging

### Enable Verbose Mode

```python
chain = LLMChain(
    llm=self.llm,
    prompt=prompt,
    verbose=True  # Shows detailed execution
)
```

### View Chain Inputs/Outputs

```python
# Before
input_data = {"query": user_query}
logger.info(f"Chain input: {input_data}")

# Execute
result = await chain.arun(**input_data)

# After
logger.info(f"Chain output: {result}")
```

### Check LangSmith

Every chain execution is automatically traced in LangSmith:
1. Go to https://smith.langchain.com
2. Open project: ai-product-recommendation-chatbot
3. View chain executions with full details

## 📚 Additional Resources

### LangChain Documentation
- **Chains**: https://python.langchain.com/docs/modules/chains/
- **LLMChain**: https://python.langchain.com/docs/modules/chains/foundational/llm_chain
- **SequentialChain**: https://python.langchain.com/docs/modules/chains/foundational/sequential_chains
- **Custom Chains**: https://python.langchain.com/docs/modules/chains/how_to/custom_chain

### LangSmith Integration
- **Tracing**: https://docs.smith.langchain.com/tracing
- **Debugging**: https://docs.smith.langchain.com/cookbook/testing-examples

## 🎓 Learning Path

1. **Understand Prompts** → Edit templates in `_build_chains()`
2. **Understand Chains** → See how chains connect inputs to outputs
3. **Understand Workflow** → Follow `execute_query()` step by step
4. **View Traces** → Watch execution in LangSmith
5. **Customize** → Add your own chains and logic

## ✨ Benefits of This Implementation

✅ **Simpler**: Easier to understand than graph-based approach
✅ **Maintainable**: Clear, linear execution flow
✅ **Debuggable**: Easy to add logging and breakpoints
✅ **Flexible**: Still supports conditional logic and branching
✅ **Traceable**: Full LangSmith integration
✅ **Production-Ready**: Robust error handling

## 🚀 Getting Started

The chatbot service is automatically initialized when the application starts. No additional setup required!

```bash
# Start the application
docker-compose up -d

# Make a request
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-User-ID: user_001" \
  -d '{"query": "I need wireless headphones"}'

# View trace in LangSmith
https://smith.langchain.com
```

Your LangChain-powered chatbot is ready to use! 🎉
