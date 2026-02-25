# Product Recommendation Chatbot

A production-ready AI-powered chatbot that recommends BestBuy Canada products based on user needs, using RAG (Retrieval-Augmented Generation) with LangChain and Pinecone.

---

## 🎉 What's New

### Recent Features (February 2026)

**🆕 User Account Information**
- Ask "Show my account info" to see your profile details
- Displays name, email, and phone in a beautiful gradient card

**🆕 Purchase History Viewer**
- Ask "Show my purchase history" to view all past orders
- Collapsible order cards with full line item details
- Product images, quantities, and prices displayed
- Automatic filtering of environmental fees

**🆕 Purchase History Loading Script**
- New `load_purchase_history.py` script to load order data
- Automatically filters environmental fees during import
- Supports multiple users with separate JSON files

**✨ UI Improvements**
- Automatic CTA banner displayed after product results (moved from AI prompt to UI)
- Collapsible order interface for better user experience
- Enhanced source indicators for all response types

---

## 🚀 Features

- **Tool-Calling Agent** — Single LangChain agent with 6 tools that handles all user intents (search, email, purchase, account info, order history, web search)
- **Intelligent Product Search** — Pinecone vector similarity search over BestBuy Canada catalogue data
- **Self-Querying Retriever (SQR)** — Single LangChain component that decomposes a natural language query into a semantic search string **and** a structured Pinecone metadata filter in one LLM call — no manual JSON parsing or separate rephrase step
- **Metadata Filtering** — Filters on `categoryName`, `salePrice`, `customerRating`, and `isOnSale` are built automatically by SQR and applied natively in Pinecone
- **User Management** — MongoDB-based user profiles (name, email, phone) used in responses and actions
- **Account Information Display** — Users can ask to see their account details (name, email, phone)
- **Purchase History Viewer** — Users can view their past orders with collapsible UI showing all line items with images
- **Email & Purchase Actions** — Triggered by UI buttons or free-text (e.g. "send it to my email")
- **Automatic CTA Display** — After showing products, a call-to-action banner is always displayed in the UI
- **Optimistic UI** — "Alright [Name], let me help you with that. Give me a second! ⏳" shown instantly while the API responds
- **Category Registry** — All unique `categoryName` values are extracted at load time and saved for filter prompting
- **Web Search Integration** — Tavily-powered web search for general questions
- **LangSmith Tracing** — Full observability of every chain execution
- **Modern UI** — Responsive React + Tailwind CSS interface

---

## 📋 Technology Stack

### Backend
| Technology | Role |
|---|---|
| FastAPI (Python 3.11+) | REST API framework |
| LangChain | Tool-calling agent with 6 tools, SelfQueryingRetriever |
| Ollama (`gpt-oss:20b` + `mxbai-embed-large`) | Local LLM inference & embeddings |
| Pinecone | Vector database with metadata filtering |
| MongoDB | User profile & purchase history storage |
| Tavily | Web search API |
| UV | Python package manager |
| LangSmith | Tracing & debugging |

### Frontend
| Technology | Role |
|---|---|
| React 18 | UI framework |
| Vite | Build tool |
| Tailwind CSS | Styling |
| Axios | HTTP client |
| Lucide React | Icons |

### Infrastructure
- Docker & Docker Compose
- Nginx reverse proxy

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│                  React UI                   │
│  - Optimistic "Give me a second!" message  │
│  - Product cards with Email/Purchase btns  │
│  - User info card (name, email, phone)     │
│  - Collapsible purchase history cards      │
│  - Automatic CTA banner for products       │
└────────────────────┬────────────────────────┘
                     │ POST /api/v1/chat
                     │ { query, last_product_ids }
                     ▼
┌─────────────────────────────────────────────┐
│              FastAPI Backend                │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │    LangChain Tool-Calling Agent     │   │
│  │                                     │   │
│  │  Agent analyzes query and calls:    │   │
│  │                                     │   │
│  │  Tool 1: search_products            │   │
│  │    → SelfQueryingRetriever          │   │
│  │    → Pinecone search with filters   │   │
│  │                                     │   │
│  │  Tool 2: send_product_email         │   │
│  │    → Email service                  │   │
│  │                                     │   │
│  │  Tool 3: purchase_product           │   │
│  │    → Purchase simulation            │   │
│  │                                     │   │
│  │  Tool 4: search_web                 │   │
│  │    → Tavily API                     │   │
│  │                                     │   │
│  │  Tool 5: get_user_info 🆕           │   │
│  │    → Returns user account details   │   │
│  │                                     │   │
│  │  Tool 6: get_purchase_history 🆕    │   │
│  │    → MongoDB query for orders       │   │
│  │                                     │   │
│  └─────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
        │            │            │
        ▼            ▼            ▼
   ┌─────────┐  ┌────────┐  ┌────────────┐
   │Pinecone │  │MongoDB │  │Tavily API  │
   │(Products)  │(Users) │  │(Web Search)│
   │         │  │(Orders)│  └────────────┘
   └─────────┘  └────────┘
```

---

## 🔄 Workflow Details

### Chat Flow (Agent-Based)

```
User types: "show me laptops under $1500 that are on sale"
                │
                ▼
Agent Execution
  ├─ Analyzes query with LLM
  ├─ Selects appropriate tool: search_products
  │
  ▼
Tool: search_products
  ├─ SelfQueryingRetriever (single LLM call)
  │  ├─ LLM decomposes query into:
  │  │    semantic string: "laptop sale discount under 1500"
  │  │    filter: {
  │  │      "categoryName": { "$eq": "Laptops" },
  │  │      "salePrice":    { "$lte": 1500 },
  │  │      "isOnSale":     { "$eq": true }
  │  │    }
  │  └─ Pinecone similarity search with filter
  │
  ├─ Stores products in AgentState
  └─ Returns formatted product list to agent
                │
                ▼
Agent generates friendly response
                │
                ▼
Return to frontend
{ message, products[], source: "vector_db" }
                │
                ▼
UI displays products + automatic CTA banner
```

### User Account Info Flow (New)

```
User types: "show my account info"
                │
                ▼
Agent Execution
  ├─ Analyzes query with LLM
  ├─ Selects appropriate tool: get_user_info
  │
  ▼
Tool: get_user_info
  ├─ Retrieves user info from injected context
  ├─ Stores user_info in AgentState
  └─ Returns formatted account details
                │
                ▼
Agent generates friendly response
                │
                ▼
Return to frontend
{ message, user_info: {name, email, phone}, source: "user_info" }
                │
                ▼
UI displays user info card with gradient design
```

### Purchase History Flow (New)

```
User types: "show my purchase history"
                │
                ▼
Agent Execution
  ├─ Analyzes query with LLM
  ├─ Selects appropriate tool: get_purchase_history
  │
  ▼
Tool: get_purchase_history
  ├─ Queries MongoDB: get_user_orders(user_id)
  ├─ Stores purchase_history in AgentState
  └─ Returns formatted order summary
                │
                ▼
Agent generates friendly response
                │
                ▼
Return to frontend
{ message, purchase_history: [orders...], source: "purchase_history" }
                │
                ▼
UI displays collapsible order cards
```

### Action Flow (Email/Purchase)

When a user types something like *"email me the MacBook"* or *"I'll take it"*:

```
User message + last_product_ids (from frontend state)
                │
                ▼
Agent Execution
  ├─ Analyzes query with LLM
  ├─ Determines action needed (email or purchase)
  ├─ Identifies product from context
  │
  ▼
Tool: send_product_email OR purchase_product
  ├─ Retrieves product from Pinecone by SKU
  ├─ Executes action (send email or simulate purchase)
  ├─ Stores result in AgentState
  └─ Returns confirmation message
                │
                ▼
Agent generates confirmation response
                │
                ▼
Return to frontend
{ message: "Done! Sent to kai@...", source: "action" }
```

---

## 🛠️ Agent Tools

The chatbot uses a LangChain tool-calling agent with 6 tools. The LLM automatically selects the appropriate tool(s) based on the user's query:

### 1. **search_products**
- **Purpose:** Search the product catalog
- **When Used:** Product searches, recommendations, availability questions
- **Implementation:** SelfQueryingRetriever with Pinecone vector search
- **Example:** "Show me gaming laptops under $2000"

### 2. **send_product_email**
- **Purpose:** Email product details to the user
- **When Used:** "Email me the details", "Send that to my email"
- **Implementation:** SMTP email service with product template
- **Example:** "Can you email me the MacBook details?"

### 3. **purchase_product**
- **Purpose:** Simulate placing an order
- **When Used:** "I'll take it", "Purchase the laptop", "Buy now"
- **Implementation:** Order simulation with confirmation
- **Example:** "I want to buy the Sony headphones"

### 4. **search_web**
- **Purpose:** Search the web for general information
- **When Used:** Questions not related to product search
- **Implementation:** Tavily API for web search
- **Example:** "What's the difference between OLED and QLED?"

### 5. **get_user_info** (New)
- **Purpose:** Display user account information
- **When Used:** "Show my account info", "What's my email?"
- **Implementation:** Returns user profile from context
- **Example:** "Can you show my account details?"

### 6. **get_purchase_history** (New)
- **Purpose:** Display user's past orders
- **When Used:** "Show my purchase history", "What have I ordered?"
- **Implementation:** MongoDB query filtered by userId
- **Example:** "Display my order history"

The agent intelligently routes queries to the appropriate tool(s) and can call multiple tools in sequence if needed.

---

## 📦 Data Format

### Products

Products are loaded from BestBuy Canada JSON files with the structure:

```json
{
  "products": [
    {
      "sku": "18470962",
      "name": "Apple AirPods 4 ...",
      "shortDescription": "Rebuilt for exceptional comfort...",
      "customerRating": 4.0,
      "productUrl": "/en-ca/product/.../18470962",
      "regularPrice": 179.99,
      "salePrice": 149.99,
      "saleEndDate": 1771574399000,
      "categoryName": "Wireless Earbuds & Earphones"
    }
  ]
}
```

The loader transforms each product to:
- Prefix `productUrl` with `https://www.bestbuy.ca`
- Derive `isOnSale = saleEndDate !== null`
- Store `text = name + " " + shortDescription` as the Pinecone embedding text
- Store all fields as Pinecone metadata for filtering

### Purchase History (New)

Purchase history is loaded from JSON files with the structure:

```json
{
  "orders": [
    {
      "orderNumber": "1019026365",
      "datetime": "2024-09-06T03:28:26Z",
      "totalPrice": 282.47,
      "status": "InProcess",
      "lineItems": [
        {
          "name": "Logitech Pebble 2 M350s Mouse",
          "sku": "17242194",
          "quantity": 1,
          "total": 29.99,
          "imgUrl": "https://multimedia.bbycastatic.ca/...",
          "parentSku": null,
          "productType": null
        }
      ]
    }
  ]
}
```

The loader (`load_purchase_history.py`) automatically:
- Filters out environmental fees (items where `parentSku` is not null/empty)
- Recalculates order totals based on filtered line items
- Excludes `parentSku` and `productType` fields from saved data
- Stores orders in MongoDB `purchase_orders` collection

### Category Registry

After loading, all unique `categoryName` values are saved to `backend/data/categories.json`:

```json
{
  "categories": ["Apple MacBook Air", "Laptops", "Wireless Earbuds & Earphones"],
  "total": 3
}
```

This file is read at startup by `ChatbotService._load_categories()` and injected into the `SelfQueryingRetriever`'s `AttributeInfo` description for `categoryName`, so the LLM inside SQR knows exactly which values are valid to filter on. Re-run `load_products.py` whenever the product catalogue changes to keep this in sync.

### MongoDB Collections

The application uses two MongoDB collections:

**users**
```json
{
  "userId": "user_001",
  "firstName": "Kai",
  "lastName": "He",
  "email": "kai.he@example.com",
  "phone": "+1234567890",
  "createdAt": "2024-01-01T00:00:00Z",
  "updatedAt": "2024-01-01T00:00:00Z"
}
```
- **Indexes:** userId (unique), email
- **Purpose:** User profiles for personalization and actions

**purchase_orders** (New)
```json
{
  "userId": "user_001",
  "orderNumber": "1019026365",
  "orderDate": "2024-09-06T03:28:26Z",
  "totalPrice": 282.47,
  "status": "InProcess",
  "lineItems": [
    {
      "name": "Logitech Pebble 2 M350s Mouse",
      "sku": "17242194",
      "quantity": 1,
      "total": 29.99,
      "imgUrl": "https://multimedia.bbycastatic.ca/..."
    }
  ],
  "createdAt": "2024-02-22T00:00:00Z",
  "updatedAt": "2024-02-22T00:00:00Z"
}
```
- **Indexes:** userId, orderNumber (unique)
- **Purpose:** Purchase history for the get_purchase_history tool
- **Note:** Environmental fees are filtered out during loading

---

## 📋 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/chat` | Chat (agent-based with 6 tools) |
| `POST` | `/api/v1/actions` | Execute email/purchase via button |
| `POST` | `/api/v1/users` | Create user |
| `GET` | `/api/v1/users/{user_id}` | Get user |

### `POST /api/v1/chat` — Request Body

```json
{
  "query": "show me headphones under $200",
  "conversation_id": "conv_abc123",
  "last_product_ids": ["18470962", "18470963"]
}
```

- `last_product_ids`: SKUs of products shown in the previous assistant message. The frontend tracks and sends these automatically to enable contextual actions.

### `POST /api/v1/chat` — Response Body

```json
{
  "message": "Here are some great headphones under $200...",
  "products": [
    {
      "sku": "18470962",
      "name": "Apple AirPods 4",
      "shortDescription": "Exceptional comfort...",
      "customerRating": 4.0,
      "regularPrice": 179.99,
      "salePrice": 149.99,
      "isOnSale": true
    }
  ],
  "conversation_id": "conv_abc123",
  "has_results": true,
  "source": "vector_db",
  "user_info": null,
  "purchase_history": []
}
```

**New Response Fields:**
- `user_info`: User account details when displaying profile (firstName, lastName, email, phone)
- `purchase_history`: Array of orders when displaying order history
- `source`: Now includes "user_info" and "purchase_history" values

---

## 🚦 Prerequisites

- Docker & Docker Compose
- Ollama running locally with `gpt-oss:20b` and `nomic-embed-text` models
- Pinecone API key (free tier available at pinecone.io)
- SMTP credentials (optional — enables real email sending)

---

## 📦 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd product-recommendation-chatbot
```

### 2. Configure Environment

```bash
cd backend
cp .env.example .env
# Edit .env — add your PINECONE_API_KEY, SMTP credentials
```

### 3. Add Product Data

Place your BestBuy JSON files in `backend/data/products/`:

```
backend/data/products/
├── laptops.json
└── headphones.json
```

Each file must use the `{ "products": [...] }` wrapper format.

### 4. Start Services

```bash
cd ..
docker-compose up -d
```

### 5. Pull Ollama Models

```bash
docker exec -it product_chatbot_ollama ollama pull gpt-oss:20b
docker exec -it product_chatbot_ollama ollama pull nomic-embed-text
```

### 6. Initialize Database & Load Data

```bash
# Create sample users in MongoDB
docker exec -it product_chatbot_backend python -m scripts.init_db

# Load products into Pinecone + save categories.json
docker exec -it product_chatbot_backend python -m scripts.load_products

# Load purchase history into MongoDB (new)
docker exec -it product_chatbot_backend python -m scripts.load_purchase_history --clear
```

**What each script does:**

`init_db.py`:
- Creates sample user accounts in MongoDB

`load_products.py`:
1. Parse all JSON files in `data/products/` (supporting the `{ "products": [] }` format)
2. Transform and validate each product
3. Save unique `categoryName` values to `data/categories.json`
4. Upsert all products into Pinecone with full metadata

`load_purchase_history.py` (new):
1. Parse purchase history JSON files for each user
2. Filter out environmental fees (items with `parentSku`)
3. Recalculate order totals
4. Store orders in MongoDB `purchase_orders` collection

### 7. Access the Application

| Service | URL |
|---|---|
| Frontend Chat UI | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| LangSmith Traces | https://smith.langchain.com |

---

## 🎯 Example Interactions

**Product search with filters:**
> "Show me laptops under $1500 that are highly rated"
→ Agent calls search_products tool
→ SQR extracts: `salePrice ≤ 1500`, `customerRating ≥ 4.0`
→ Pinecone filtered search → product cards + automatic CTA banner

**Account information:**
> "Can you show my account info?"
→ Agent calls get_user_info tool
→ User info card displays: Name, Email, Phone

**Purchase history:**
> "Show me my purchase history"
→ Agent calls get_purchase_history tool
→ MongoDB query for orders
→ Collapsible order cards display with all line items

**Free-text email intent:**
> "Can you send the MacBook to my email?"
→ Agent calls send_product_email tool with MacBook SKU from context
→ Email sent → confirmation message

**Free-text purchase intent:**
> "I'll take the Sony ones"
→ Agent calls purchase_product tool with Sony product SKU from context
→ Order simulated → order ID returned

**On-sale filter:**
> "Any headphones on sale right now?"
→ Agent calls search_products tool
→ SQR extracts: `isOnSale: true`, `categoryName: "Wireless Earbuds & Earphones"`
→ Filtered Pinecone search

**General questions with web search:**
> "What's the difference between OLED and QLED TVs?"
→ Agent calls search_web tool (Tavily)
→ Web search results → informative response

---

## 🗂️ Project Structure

```
product-recommendation-chatbot/
├── backend/
│   ├── app/
│   │   ├── models/
│   │   │   ├── product.py          # ProductBase (BestBuy fields), ProductDocument
│   │   │   ├── request.py          # ChatRequest, ChatResponse (+ user_info, purchase_history)
│   │   │   ├── state.py            # AgentState (+ user_info, purchase_history fields)
│   │   │   ├── user.py             # UserInDB (name, email, phone)
│   │   │   └── order.py 🆕         # OrderInDB, LineItem models
│   │   ├── database/
│   │   │   ├── mongodb.py          # User & order CRUD, indexes
│   │   │   └── pinecone_db.py      # build_sqr() factory, add_products, get_product_by_id
│   │   ├── services/
│   │   │   ├── chatbot_service.py  # Tool-calling agent with 6 tools
│   │   │   ├── data_loader.py      # BestBuy format support + category extraction
│   │   │   ├── email_service.py
│   │   │   ├── user_service.py
│   │   │   └── tavily_service.py   # Web search
│   │   ├── tools/
│   │   │   ├── search_tool.py      # search_products tool
│   │   │   ├── email_tool.py       # send_product_email tool
│   │   │   ├── purchase_tool.py    # purchase_product tool
│   │   │   ├── web_search_tool.py  # search_web tool (Tavily)
│   │   │   ├── user_info_tool.py 🆕 # get_user_info tool
│   │   │   └── purchase_history_tool.py 🆕 # get_purchase_history tool
│   │   ├── api/
│   │   │   └── routes.py           # /chat passes user_info & purchase_history
│   │   └── config.py               # Settings with mongodb_purchase_orders_collection
│   ├── data/
│   │   ├── products/               # BestBuy JSON files (laptops.json, headphones.json)
│   │   ├── categories.json         # Auto-generated by load_products.py
│   │   └── purchase_history/       # Purchase history JSON files 🆕
│   │       ├── purchase_history_user_001.json
│   │       ├── purchase_history_user_002.json
│   │       └── purchase_history_user_003.json
│   └── scripts/
│       ├── init_db.py              # Create sample users
│       ├── load_products.py        # Load products + save categories.json
│       └── load_purchase_history.py 🆕 # Load purchase history into MongoDB
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── ChatInterface.jsx   # Main UI with user selector
│       │   ├── MessageList.jsx     # Renders messages, products, user info, orders
│       │   ├── InputBox.jsx
│       │   └── ProductCard.jsx
│       ├── hooks/
│       │   └── useChat.js          # Optimistic message, handles userInfo & purchaseHistory
│       └── services/
│           └── api.js              # sendMessage includes last_product_ids
├── docker-compose.yml
└── README.md
```

---

## 🔍 LangSmith Tracing

Every chain execution is automatically traced. View at https://smith.langchain.com.

**Trace structure examples:**
```
User query: "show me my account info"
├─ Agent execution                                                          (1.2s)
│  ├─ LLM analyzes query                                                    (0.8s)
│  └─ Tool call: get_user_info                                              (0.1s)
│     └─ Returns user account details
└─ Agent generates response                                                 (0.3s)

─────────────────────────────────────────────────────────────────────────────
User query: "show my purchase history"
├─ Agent execution                                                          (1.5s)
│  ├─ LLM analyzes query                                                    (0.7s)
│  └─ Tool call: get_purchase_history                                       (0.5s)
│     └─ MongoDB query: get_user_orders()                                   (0.4s)
│     └─ Returns 5 orders
└─ Agent generates response                                                 (0.3s)

─────────────────────────────────────────────────────────────────────────────
User query: "laptops on sale under $2000"
├─ Agent execution                                                          (2.8s)
│  ├─ LLM analyzes query                                                    (0.8s)
│  └─ Tool call: search_products                                            (1.7s)
│     └─ SelfQueryingRetriever
│        ├─ LLM decomposes query                                            (1.1s)
│        │  ├─ semantic string: "laptop sale discount"
│        │  └─ filter: { categoryName: "Laptops", salePrice: ≤2000, isOnSale: true }
│        └─ Pinecone search                                                 (0.6s)
│           └─ Returns 4 products
└─ Agent generates response                                                 (0.3s)

─────────────────────────────────────────────────────────────────────────────
User query: "email me the MacBook"
├─ Agent execution                                                          (1.5s)
│  ├─ LLM analyzes query                                                    (0.8s)
│  └─ Tool call: send_product_email                                         (0.4s)
│     └─ Email sent to kai@example.com
└─ Agent generates confirmation                                             (0.3s)
```

All tool calls, LLM interactions, and data flows are visible in LangSmith for debugging and optimization.

---

## 🛠️ Troubleshooting

**No products returned despite correct query:**
- Check `categories.json` exists in `backend/data/` — if missing, re-run `load_products.py`
- Verify Pinecone index has vectors: check `/api/v1/health` and Pinecone dashboard
- Check LangSmith trace for the search_products tool — look at what filter SQR generated; it may be too restrictive

**SQR generating wrong or overly strict filters:**
- Inspect the SQR trace in LangSmith — the `query_constructor` sub-chain shows the exact filter generated
- If a category is not in `categories.json`, SQR won't use it — re-run `load_products.py` to regenerate
- If filters are too aggressive, consider removing the `categoryName` filter from the query and letting semantic search handle it

**User info not displaying:**
- Verify user exists in MongoDB: `docker exec -it product_chatbot_mongo mongosh product_chatbot --eval "db.users.findOne()"`
- Check that the query clearly asks for account information

**Purchase history not displaying:**
- Verify purchase history was loaded: `docker exec -it product_chatbot_mongo mongosh product_chatbot --eval "db.purchase_orders.countDocuments()"`
- Re-run loading script: `docker exec -it product_chatbot_backend python -m scripts.load_purchase_history --clear`
- Check backend logs for MongoDB connection errors

**Environmental fees appearing in orders:**
- Re-run the loading script with `--clear` flag to reload with proper filtering
- Script automatically filters items where `parentSku` is not null

**Agent not calling the right tool:**
- Check LangSmith trace to see which tool was selected
- Verify the query clearly indicates the desired action
- The agent uses the LLM to intelligently route requests

**Email not sending:**
- Verify SMTP credentials in `.env`
- The service logs the error but returns a graceful failure message

---

## 📝 Environment Variables

```env
# Pinecone
PINECONE_API_KEY=your_key
PINECONE_INDEX_NAME=product-recommendations
PINECONE_DIMENSION=768
PINECONE_NAMESPACE=products

# Ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=gpt-oss:20b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# MongoDB
MONGODB_URL=mongodb://mongodb:27017
MONGODB_DB_NAME=chatbot
MONGODB_USER_COLLECTION=users
MONGODB_PURCHASE_ORDERS_COLLECTION=purchase_orders


# LangSmith (optional)
LANGSMITH_API_KEY=your_key
LANGSMITH_PROJECT=product-chatbot
LANGSMITH_TRACING=true

# Search (SQR uses TOP_K; threshold filtering is handled by Pinecone natively via SQR)
SEARCH_TOP_K=5

# SMTP (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your_password
SMTP_FROM=your@email.com
```

---

## 🚀 Quick Commands Reference

### Start/Stop Services
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Data Loading
```bash
# Load products into Pinecone
docker exec -it product_chatbot_backend python -m scripts.load_products

# Load purchase history into MongoDB (includes filtering)
docker exec -it product_chatbot_backend python -m scripts.load_purchase_history --clear

# Initialize sample users
docker exec -it product_chatbot_backend python -m scripts.init_db
```

### MongoDB Operations
```bash
# Check purchase orders count
docker exec -it product_chatbot_mongo mongosh product_chatbot --eval "db.purchase_orders.countDocuments()"

# View all orders for a user
docker exec -it product_chatbot_mongo mongosh product_chatbot --eval "db.purchase_orders.find({userId: 'user_001'}).pretty()"

# Check users
docker exec -it product_chatbot_mongo mongosh product_chatbot --eval "db.users.find().pretty()"
```

### Testing
```bash
# Test API health
curl http://localhost:8000/api/v1/health

# View API docs
open http://localhost:8000/docs
```

### New Feature Testing Queries
```
"Show my account info"
"What's my email address?"
"Show my purchase history"
"What have I ordered before?"
"Display my past orders"
```

---

## 📚 Additional Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Quick setup guide
- **[SETUP_LOCAL_OLLAMA.md](SETUP_LOCAL_OLLAMA.md)** - Ollama configuration
- **[LANGCHAIN_IMPLEMENTATION.md](LANGCHAIN_IMPLEMENTATION.md)** - LangChain architecture details
- **[LANGSMITH_GUIDE.md](LANGSMITH_GUIDE.md)** - LangSmith tracing setup
- **[NEW_FEATURES_SUMMARY.md](NEW_FEATURES_SUMMARY.md)** - User info & purchase history features
- **[TESTING_GUIDE_NEW_FEATURES.md](TESTING_GUIDE_NEW_FEATURES.md)** - Test scenarios for new features

---

## 📄 License

[Your License Here]

---

## 🤝 Contributing

Contributions are welcome! Please read the contributing guidelines before submitting PRs.

---

## 📧 Support

For issues or questions, please open an issue on GitHub or contact the development team.

