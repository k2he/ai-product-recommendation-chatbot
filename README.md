# Product Recommendation Chatbot

A production-ready AI-powered chatbot that recommends BestBuy Canada products based on user needs, using RAG (Retrieval-Augmented Generation) with LangChain and Pinecone.

---

## 🚀 Features

- **Smart Intent Detection** — LLM classifies every message as search, email, or purchase before any search is performed
- **Intelligent Product Search** — Pinecone vector similarity search over BestBuy Canada catalogue data
- **Self-Querying Retriever (SQR)** — Single LangChain component that decomposes a natural language query into a semantic search string **and** a structured Pinecone metadata filter in one LLM call — no manual JSON parsing or separate rephrase step
- **Metadata Filtering** — Filters on `categoryName`, `salePrice`, `customerRating`, and `isOnSale` are built automatically by SQR and applied natively in Pinecone
- **User Management** — MongoDB-based user profiles (name, email) used in responses and actions
- **Email & Purchase Actions** — Triggered by UI buttons or free-text (e.g. "send it to my email")
- **Purchase CTA in every response** — After showing products, the assistant always asks if the user wants to email or purchase
- **Optimistic UI** — "Alright [Name], let me help you with that. Give me a second! ⏳" shown instantly while the API responds
- **Category Registry** — All unique `categoryName` values are extracted at load time and saved for filter prompting
- **LangSmith Tracing** — Full observability of every chain execution
- **Modern UI** — Responsive React + Tailwind CSS interface

---

## 📋 Technology Stack

### Backend
| Technology | Role |
|---|---|
| FastAPI (Python 3.11+) | REST API framework |
| LangChain | AI workflow: intent_chain, SelfQueryingRetriever, response_chain |
| Ollama (`gpt-oss:20b` + `nomic-embed-text`) | Local LLM inference & embeddings |
| Pinecone | Vector database with metadata filtering |
| MongoDB | User profile storage |
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
│  - Tracks lastProductIds for intent        │
└────────────────────┬────────────────────────┘
                     │ POST /api/v1/chat
                     │ { query, last_product_ids }
                     ▼
┌─────────────────────────────────────────────┐
│              FastAPI Backend                │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │       LangChain Workflow            │   │
│  │                                     │   │
│  │  Step 0: intent_chain (LLM)         │   │
│  │    → "search" / "email" / "purchase"│   │
│  │         │                           │   │
│  │    ┌────┴────────────┐              │   │
│  │    │ email/purchase  │  search      │   │
│  │    ▼                 ▼              │   │
│  │  execute_action  SelfQueryingRetriever   │
│  │  (skip search)   (Steps 1+3 merged) │   │
│  │                  ├─ LLM decomposes  │   │
│  │                  │  query → string  │   │
│  │                  │  + filter dict   │   │
│  │                  └─ Pinecone search │   │
│  │                     with filter     │   │
│  │                      │             │   │
│  │                  MongoDB (user)     │   │
│  │                      │             │   │
│  │                      │             │   │
│  │                  response_chain     │   │
│  │                  + CTA (LLM)        │   │
│  └─────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
        │            │
        ▼            ▼
   ┌─────────┐  ┌────────┐
   │Pinecone │  │MongoDB │
   └─────────┘  └────────┘
```

---

## 🔄 Workflow Details

### Chat Flow (Step by Step)

```
User types: "show me laptops under $1500 that are on sale"
                │
                ▼
Step 0 ── intent_chain (LLM)
          Output: { "intent": "search", "product_hint": null }
                │
                ▼ (intent = "search")
Step 1 ── MongoDB → fetch user (name, email)
                │
                ▼
Steps  ── SelfQueryingRetriever (single LLM call — replaces old rephrase + filter steps)
2 + 3     ┌─ LLM decomposes query into:
          │    semantic string: "laptop sale discount under 1500"
          │    filter: {
          │      "categoryName": { "$eq": "Laptops" },
          │      "salePrice":    { "$lte": 1500 },
          │      "isOnSale":     { "$eq": true }
          │    }
          └─ Pinecone similarity search with filter applied natively
                │
                ▼
Step 4 ── response_chain (LLM)
          Generates friendly response + mandatory CTA:
          "Would you like me to send these to your email, or purchase one?"
                │
                ▼
        Return to frontend
        { message, products[], source }
```

### Intent-Based Action Flow (New)

When a user types something like *"email me the MacBook"* or *"I'll take it"*:

```
User message + last_product_ids (from frontend state)
                │
                ▼
Step 0 ── intent_chain (LLM)
          Output: { "intent": "email", "product_hint": "MacBook" }
                │
                ▼ (intent ≠ "search", last_product_ids present)
          Match product_hint against last shown products
          → resolve target product SKU
                │
                ▼
          execute_action("email" | "purchase", product_id, user_id)
          → email_service.send_product_email() OR
          → purchase simulation (order ID returned)
                │
                ▼
          Return confirmation message (no products in response)
          { message: "Done! Sent to kai@...", source: "action" }
```

### Button Action Flow (Existing)

Clicking Email / Purchase buttons on a product card sends directly to `POST /api/v1/actions` — bypassing chat and intent detection entirely.

---

## 📦 Data Format

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

### Category Registry

After loading, all unique `categoryName` values are saved to `backend/data/categories.json`:

```json
{
  "categories": ["Apple MacBook Air", "Laptops", "Wireless Earbuds & Earphones"],
  "total": 3
}
```

This file is read at startup by `ChatbotService._load_categories()` and injected into the `SelfQueryingRetriever`'s `AttributeInfo` description for `categoryName`, so the LLM inside SQR knows exactly which values are valid to filter on. Re-run `load_products.py` whenever the product catalogue changes to keep this in sync.

---

## 📋 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/chat` | Chat (search + intent detection) |
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

- `last_product_ids`: SKUs of products shown in the previous assistant message. The frontend tracks and sends these automatically to enable free-text email/purchase intents.

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

### 6. Initialize Database & Load Products

```bash
# Create sample users in MongoDB
docker exec -it product_chatbot_backend python scripts/init_db.py

# Load products into Pinecone + save categories.json
docker exec -it product_chatbot_backend python scripts/load_products.py
```

`load_products.py` will:
1. Parse all JSON files in `data/products/` (supporting the `{ "products": [] }` format)
2. Transform and validate each product
3. Save unique `categoryName` values to `data/categories.json`
4. Upsert all products into Pinecone with full metadata

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
→ LLM extracts: `salePrice ≤ 1500`, `customerRating ≥ 4.0`
→ Pinecone filtered search → product cards + CTA

**Free-text email intent:**
> "Can you send the MacBook to my email?"
→ LLM detects `intent: email`, matches "MacBook" in last shown products
→ Email sent → confirmation message (no new search)

**Free-text purchase intent:**
> "I'll take the Sony ones"
→ LLM detects `intent: purchase`, matches "Sony" in last shown products
→ Order simulated → order ID returned

**On-sale filter:**
> "Any headphones on sale right now?"
→ LLM extracts: `isOnSale: true`, `categoryName: { $in: ["Wireless Earbuds & Earphones"] }`
→ Filtered Pinecone search

---

## 🗂️ Project Structure

```
product-recommendation-chatbot/
├── backend/
│   ├── app/
│   │   ├── models/
│   │   │   ├── product.py          # ProductBase (BestBuy fields), ProductDocument
│   │   │   ├── request.py          # ChatRequest (+ last_product_ids), ActionRequest
│   │   │   └── user.py
│   │   ├── database/
│   │   │   ├── mongodb.py
│   │   │   └── pinecone_db.py      # build_sqr() factory, add_products, get_product_by_id
│   │   ├── services/
│   │   │   ├── chatbot_service.py  # intent_chain, SQR (_run_sqr), response_chain
│   │   │   ├── data_loader.py      # BestBuy format support + category extraction
│   │   │   ├── email_service.py
│   │   │   └── user_service.py
│   │   ├── api/
│   │   │   └── routes.py           # /chat passes last_product_ids to service
│   │   └── config.py
│   ├── data/
│   │   ├── products/               # BestBuy JSON files (laptops.json, headphones.json)
│   │   └── categories.json         # Auto-generated by load_products.py
│   └── scripts/
│       ├── init_db.py
│       └── load_products.py        # Loads products + saves categories.json
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── ChatInterface.jsx   # Passes userName to useChat
│       │   ├── MessageList.jsx
│       │   ├── InputBox.jsx
│       │   └── ProductCard.jsx
│       ├── hooks/
│       │   └── useChat.js          # Optimistic message, lastProductIds tracking
│       └── services/
│           └── api.js              # sendMessage includes last_product_ids
├── docker-compose.yml
└── README.md
```

---

## 🔍 LangSmith Tracing

Every chain execution is automatically traced. View at https://smith.langchain.com.

**Trace structure per request:**
```
User query: "email me the MacBook"
├─ intent_chain            → { intent: "email", product_hint: "MacBook" }  (0.8s)
│
└─ execute_action          → email sent to kai@example.com                  (0.3s)

─────────────────────────────────────────────────────
User query: "laptops on sale under $2000"
├─ intent_chain            → { intent: "search" }                           (0.7s)
├─ MongoDB                 → user: Kai He                                    (0.1s)
├─ SelfQueryingRetriever   → LLM decomposes query + filter                  (1.1s)
│  ├─ semantic string:       "laptop sale discount"
│  ├─ filter:                { categoryName: "Laptops", salePrice: ≤2000,
│  │                           isOnSale: true }
│  └─ Pinecone search:       4 products returned                            (0.6s)
└─ response_chain          → friendly message + CTA                         (2.0s)
```

---

## 🛠️ Troubleshooting

**No products returned despite correct query:**
- Check `categories.json` exists in `backend/data/` — if missing, re-run `load_products.py`
- Verify Pinecone index has vectors: check `/api/v1/health` and Pinecone dashboard
- Check LangSmith trace for the SQR step — look at what filter it generated; it may be too restrictive

**SQR generating wrong or overly strict filters:**
- Inspect the SQR trace in LangSmith — the `query_constructor` sub-chain shows the exact filter generated
- If a category is not in `categories.json`, SQR won't use it — re-run `load_products.py` to regenerate
- If filters are too aggressive, consider removing the `categoryName` filter from the query and letting semantic search handle it

**Intent always resolves to "search":**
- This is the safe default — confirm `last_product_ids` is being sent from the frontend
- Check LangSmith trace for the `intent_chain` output

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
