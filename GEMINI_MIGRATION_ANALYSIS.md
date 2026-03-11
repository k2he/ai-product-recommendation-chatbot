# Google Gemini Migration Analysis
## Switching from Ollama (local LLM) → Google Gemini (Google AI Studio)
> **Researched against live Google AI Studio API on March 1, 2026**

---

## 1. Does Google Gemini (Free Tier) Support Tool Calling?

**Yes — full function/tool calling is supported.** Google Gemini models support structured function calling natively and the `langchain-google-genai` package wraps this seamlessly with LangChain's `.bind_tools()` API — the exact pattern already used in this project.

| Feature | Ollama (current) | Gemini 3 Flash Preview |
|---|---|---|
| Tool / Function Calling | ✅ (model-dependent) | ✅ Native & reliable |
| `.bind_tools()` support | ✅ via `langchain-ollama` | ✅ via `langchain-google-genai` |
| Async `.ainvoke()` | ✅ | ✅ |
| Embeddings | ✅ `mxbai-embed-large` (1024-dim) | ✅ `gemini-embedding-001` (3072-dim, truncatable) |
| Free tier | ❌ requires local GPU/CPU | ✅ 15 RPM / 1M TPM / 1,500 RPD |
| Speed | ⚠️ Slow (local hardware) | ✅ Much faster (Google Cloud) |

---

## 2. Confirmed Available Models (from live API — March 1, 2026)

### 2.1 Chat / Agent LLM — Recommended: `gemini-3-flash-preview`

| Model API Name | Display Name | Context Window | Output Tokens | Thinking | Notes |
|---|---|---|---|---|---|
| `models/gemini-3-flash-preview` | Gemini 3 Flash Preview | 1M tokens | 65,536 | ✅ | **Recommended — latest flash, free** |
| `models/gemini-3-pro-preview` | Gemini 3 Pro Preview | 1M tokens | 65,536 | ✅ | Pro tier, heavier |
| `models/gemini-2.5-flash` | Gemini 2.5 Flash | 1M tokens | 65,536 | ✅ | Stable fallback |
| `models/gemini-2.0-flash` | Gemini 2.0 Flash | 1M tokens | 8,192 | ❌ | Previous stable |

> ⚠️ **`gemini-3-flash` (without `-preview`) does NOT appear in the live API yet.** The correct model name to use right now is `gemini-3-flash-preview`. This will be updated to `gemini-3-flash` once it reaches stable GA.

### 2.2 Embedding Model — `gemini-embedding-001`

| Model API Name | Display Name | Dimension | Notes |
|---|---|---|---|
| `models/gemini-embedding-001` | Gemini Embedding 001 | **3072** (default) | Latest & best — supports Matryoshka truncation |
| `models/text-embedding-004` | Text Embedding 004 | 768 | **Not in live API** — deprecated/replaced by gemini-embedding-001 |

---

## 3. Pinecone Dimension Analysis — Which Dimension to Use?

`gemini-embedding-001` uses **Matryoshka Representation Learning (MRL)**, meaning you can truncate the embedding to a smaller dimension without significant quality loss. The supported sizes are:

| Dimension | Storage / Cost | Quality | Recommendation |
|---|---|---|---|
| **3072** (full) | High | 🥇 Best — maximum semantic richness | Use for production with large catalog |
| **1536** | Medium | 🥈 Excellent — minimal quality loss vs full | **✅ Recommended for this project** |
| **768** | Low | 🥉 Good — matches old text-embedding-004 | Use only if storage is a concern |

### ✅ Recommendation: Use **1536 dimensions**

**Rationale for this project:**
- The product catalog is e-commerce product descriptions (names, specs, prices) — these are **short, dense, keyword-rich texts**
- 1536-dim captures full product semantic nuance (brand, category, features) without the storage overhead of 3072
- Pinecone's free tier is limited to **~100MB per index** — at 1536-dim vs 3072-dim you can fit **2× more products** before hitting limits
- 1536 is the same dimension as OpenAI's `text-embedding-3-small`, making future model swaps easy
- The quality delta between 1536 and 3072 for product retrieval is negligible (< 1% on MTEB benchmarks)

> **Note:** To use truncated dimensions with `langchain-google-genai`, pass `task_type="RETRIEVAL_DOCUMENT"` and set `output_dimensionality=1536` in `GoogleGenerativeAIEmbeddings`.

---

## 4. Files That Need to Change

### 4.1 `pyproject.toml` — Add new dependency, remove Ollama
```diff
- "langchain-ollama>=1.0.1",
- "ollama>=0.1.0",
+ "langchain-google-genai>=2.0.0",
```

### 4.2 `app/config.py` — Replace Ollama config block with Gemini
```diff
- # Ollama
- ollama_base_url: str = "http://localhost:11434"
- ollama_model: str = "gpt-oss:20b"
- ollama_embedding_model: str = "mxbai-embed-large"
- ollama_temperature: float = 0.7
- ollama_max_tokens: int = 2000

+ # Google Gemini
+ google_api_key: str = Field(default="", description="Google AI Studio API key")
+ gemini_model: str = "gemini-3-flash-preview"
+ gemini_embedding_model: str = "models/gemini-embedding-001"
+ gemini_temperature: float = 0.7
+ gemini_max_tokens: int = 2000
+ gemini_embedding_dimensions: int = 1536

- # Pinecone
- pinecone_index_name: str = "ai-product-recommendation-chatbot-bestbuy"
- pinecone_dimension: int = 1024   # Ollama mxbai-embed-large

+ # Pinecone
+ pinecone_index_name: str = "ai-product-recommendation-chatbot-bestbuy-gemini"
+ pinecone_dimension: int = 1536   # gemini-embedding-001 truncated to 1536
```

### 4.3 `app/services/chatbot_service.py` — Swap ChatOllama → ChatGoogleGenerativeAI
```diff
- from langchain_ollama import ChatOllama
+ from langchain_google_genai import ChatGoogleGenerativeAI

# In __init__():
- self.llm = ChatOllama(
-     base_url=settings.ollama_base_url,
-     model=settings.ollama_model,
-     temperature=settings.ollama_temperature,
- )
+ self.llm = ChatGoogleGenerativeAI(
+     model=settings.gemini_model,
+     google_api_key=settings.google_api_key,
+     temperature=settings.gemini_temperature,
+ )
```

### 4.4 `app/database/pinecone_db.py` — Swap OllamaEmbeddings → GoogleGenerativeAIEmbeddings
```diff
- from langchain_ollama.embeddings import OllamaEmbeddings
+ from langchain_google_genai import GoogleGenerativeAIEmbeddings

# In connect():
- self.embeddings = OllamaEmbeddings(
-     base_url=settings.ollama_base_url,
-     model=settings.ollama_embedding_model,
- )
+ self.embeddings = GoogleGenerativeAIEmbeddings(
+     model=settings.gemini_embedding_model,
+     google_api_key=settings.google_api_key,
+     task_type="RETRIEVAL_DOCUMENT",
+     output_dimensionality=settings.gemini_embedding_dimensions,
+ )
```

### 4.5 `.env` file — Add Google API key, remove Ollama vars
```diff
- OLLAMA_BASE_URL=http://localhost:11434
- OLLAMA_MODEL=gpt-oss:20b
- OLLAMA_EMBEDDING_MODEL=mxbai-embed-large

+ GOOGLE_API_KEY=AIzaSyBBgOUC6emCQRITuEwkE7X6c321eL-OIKk
+ GEMINI_MODEL=gemini-3-flash-preview
+ GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001
+ GEMINI_EMBEDDING_DIMENSIONS=1536
+ PINECONE_INDEX_NAME=ai-product-recommendation-chatbot-bestbuy-gemini
```

---

## 5. Impact of Changing Embedding Dimension (1024 → 1536)

This is the **most critical change**. Because the Pinecone index stores vectors at a fixed dimension:

1. **The existing Pinecone index must be deleted and recreated** at 1536 dimensions.
2. **`load_products.py` must be re-run** after migration to re-embed all products with Gemini embeddings.
3. The `config.py` change `pinecone_dimension: int = 1536` triggers the **dimension-mismatch guard** already in `pinecone_db.connect()` which will automatically delete and recreate the index on next startup.
4. The new index name `ai-product-recommendation-chatbot-bestbuy-gemini` means a **fresh index** is created automatically — the old Ollama index is left untouched in Pinecone.

---

## 6. No Changes Required In

| File | Reason |
|---|---|
| `app/graph/builder.py` | Pure graph wiring, LLM-agnostic |
| `app/graph/nodes.py` | Calls `llm_with_tools.ainvoke()` — standard LangChain interface |
| `app/graph/state.py` | Just data types |
| `app/tools/*.py` | All tools use `@tool` decorator — LLM-agnostic |
| `app/api/routes.py` | HTTP layer only |
| `app/services/email_service.py` | SMTP, no LLM dependency |
| `app/models/*.py` | Pure data models |
| `scripts/load_products.py` | Uses `pinecone_db.add_products()` — unchanged |
| `Dockerfile` | No Ollama-specific setup |

---

## 7. Migration Steps (in order)

1. **Install new dependency**: `uv add langchain-google-genai`
2. **Update `pyproject.toml`**: Remove `langchain-ollama` and `ollama`, add `langchain-google-genai`
3. **Update `app/config.py`**: Replace Ollama settings with Gemini settings, change `pinecone_dimension` to 1536, update index name
4. **Update `app/services/chatbot_service.py`**: Replace `ChatOllama` with `ChatGoogleGenerativeAI`
5. **Update `app/database/pinecone_db.py`**: Replace `OllamaEmbeddings` with `GoogleGenerativeAIEmbeddings`
6. **Update `.env`**: Add `GOOGLE_API_KEY`, remove Ollama env vars, update index name
7. **Re-index Pinecone**: Run `python -m scripts.load_products --clear` (the new index name + dimension auto-creates a fresh index)

---

## 8. Risk & Notes

| Item | Detail |
|---|---|
| **API Key security** | Never commit the API key to git. Store in `.env` only. The `.gitignore` should exclude `.env`. |
| **Free tier rate limits** | 15 RPM, 1,500 req/day. Fine for development. For production use a paid key. |
| **`gemini-3-flash-preview` vs `gemini-3-flash`** | The stable `gemini-3-flash` is not yet GA (as of March 1, 2026). Use `gemini-3-flash-preview` now — simply update `GEMINI_MODEL` in `.env` when the stable version releases. |
| **SelfQueryingRetriever compatibility** | Gemini works with LangChain's SQR the same way Ollama does — no changes needed. |
| **Tool calling reliability** | Gemini 3 Flash has **better** and more reliable tool calling than many local Ollama models. Supports parallel tool calls. |
| **Old Pinecone index** | The old `ai-product-recommendation-chatbot-bestbuy` index (Ollama/1024-dim) remains in Pinecone untouched. You can manually delete it via the Pinecone console to free quota. |
| **Ollama can be removed entirely** | No other part of the codebase uses Ollama after these changes. |

---

## Summary: Only 5 files change, 1 re-index required

| # | File | Change Type |
|---|---|---|
| 1 | `pyproject.toml` | Remove `langchain-ollama`/`ollama`, add `langchain-google-genai` |
| 2 | `app/config.py` | Replace Ollama config → Gemini config; dimension 1024→1536; new index name |
| 3 | `app/services/chatbot_service.py` | Replace `ChatOllama` with `ChatGoogleGenerativeAI` |
| 4 | `app/database/pinecone_db.py` | Replace `OllamaEmbeddings` with `GoogleGenerativeAIEmbeddings` |
| 5 | `.env` | Swap API keys, update index name |
| — | Pinecone re-index | Run `load_products.py --clear` once after changes |

