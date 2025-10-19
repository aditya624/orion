# 🌌 Orion — Populix Knowledge Agent API

Welcome to **Orion**, a FastAPI-based backend that fulfills the "Machine Learning Engineer Technical Assignment" brief by exposing a minimal yet production-minded API for interacting with an LLM-powered agent. The agent is fine-tuned (via prompt + tools) to answer questions about **Populix**—from business model insights to product capabilities—by grounding its responses in a curated knowledge base.

---

## 🎯 Assignment Alignment
| Requirement | How Orion Delivers |
|-------------|--------------------|
| Build a functional API service on top of an open-source LLM | Uses `langchain` with the **Groq-hosted Llama 3.1** chat model plus tool bindings. |
| Provide a public API endpoint that exposes the model's reasoning ability | `/v1/agent/generate` handles authenticated question answering with retrieval augmentation. |
| Run locally or on cloud infrastructure | Runs with `uvicorn` locally or via Docker; relies on managed services (MongoDB, Qdrant, Langfuse) but can be substituted with self-hosted instances. |

---

## 🧠 High-Level Architecture Production Ready

<p align="center">
  <img src="docs/assets/populix-architecture.svg" alt="Populix agent architecture diagram showing Orion orchestrating Groq Owen 3 32B, Qdrant, MongoDB, Langfuse, and Hugging Face" width="720" />
</p>

> 📁 The source for this illustration lives at [`docs/assets/populix-architecture.svg`](docs/assets/populix-architecture.svg) so you can update or swap the file without editing the README copy.

### Component Responsibilities

| Component | Role in the Populix Agent |
|-----------|---------------------------|
| **Clients** | Populix web / internal tools send authenticated questions to Orion. |
| **Orion Service** | FastAPI handles HTTP, validates bearer tokens, and forwards work to the LangChain/LangGraph agent that chooses between retrieval, memory, and generation tools. |
| **Hugging Face Endpoint Embeddings** | Produces dense vectors for new Populix documents during ingestion. |
| **Qdrant Vector DB** | Stores embeddings and supports semantic search to supply the agent with grounded Populix knowledge. |
| **MongoDB Chat History** | Maintains per-user conversation state so follow-up questions inherit prior context. |
| **Langfuse Observability** | Tracks prompts, traces, and evaluation metrics for debugging and governance. |
| **Groq + Owen 3 32B** | Groq's accelerated inference host runs the open-source Owen 3 32B model that ultimately drafts the natural-language answer. |

> 🖼️ The layout above mirrors the provided high-level architecture diagram, with the Orion service orchestrating data flow between retrieval, memory, observability, and Groq-hosted LLM components.

---

## 🚀 Quickstart

### 1. Clone & Install (Conda)
```bash
git clone <this-repo-url>
cd orion
conda create -n orion python=3.11 -y
conda activate orion
# optional helper if you prefer scripted setup
bash scripts/init.sh
pip install -e .
```

### 2. Configure Environment
Create a `.env` file (or export variables) with only the required secrets:

```env
MONGODB_URI=<mongodb-uri>
GROQ_API_KEY=<groq-api-key>
QDRANT_API_KEY=<qdrant-api-key>
HF_TOKEN=<hf-inference-token>
LANGFUSE_SECRET_KEY=<langfuse-secret-key>
LANGFUSE_PUBLIC_KEY=<langfuse-public-key>
LANGFUSE_HOST="https://cloud.langfuse.com"
```

### 3. Run the API
```bash
uvicorn orion.main:app --reload --port 8000
```
Open http://localhost:8000/docs to explore the interactive Swagger UI.

### 4. (Optional) Docker Run
```bash
docker pull aditya624/orion:latest
docker run --env-file .env -p 8000:8000 aditya624/orion:latest
```

---

## 🔐 Authentication
All endpoints use HTTP Bearer authentication. Clients must send:

```
Authorization: Bearer <TOKEN>
```

Requests without a matching token receive `401 Unauthorized` responses.

---

## 📚 API Reference

### Agent Service (`/v1/agent`)
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Liveness probe for the agent service. |
| `POST` | `/generate` | Main entrypoint for Populix Q&A. Returns the answer and latency (ms). |
| `GET`  | `/history` | Fetches conversation history for a `user_id` + `session_id` pair, ordered ascending or descending. |

#### Generate Request Example
```bash
TOKEN="<your-api-token>"
curl -X POST http://localhost:8000/v1/agent/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "input": "Apa saja produk riset Populix untuk brand FMCG?",
        "session_id": "demo-session",
        "user_id": "demo-user"
      }'
```

### Knowledge Service (`/v1/knowledge`)
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Liveness probe for the knowledge ingestor. |
| `POST` | `/upload-link` | Deduplicates and ingests new Populix web pages. Stores chunks in Qdrant and embeddings on Hugging Face. |

#### Upload Request Example
```bash
TOKEN="<your-api-token>"
curl -X POST http://localhost:8000/v1/knowledge/upload-link \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{ "links": ["https://populix.co/insights"] }'
```

---

## 🗄️ Data & Memory Strategy
* **Retrieval-Augmented Generation (RAG):** `Knowledge.query` performs similarity search over Qdrant and injects rich context (title, URL, chunk) into the agent prompt.
* **Conversation Memory:** `MongoDBChatMessageHistory` maintains turn-by-turn chat context to support follow-up questions.
* **Analytics:** Langfuse callbacks trace every request, providing observability for debugging and product analytics.

---

## 🧪 Testing & Tooling
Run the test suite (integration-safe) with:
```bash
pytest
```
Additional recommended checks:
```bash
ruff check .
uvicorn orion.main:app --reload  # local smoke test
```

---

## 🗂️ Project Structure
```
orion/
├── orion/
│   ├── api/                 # FastAPI routers & auth
│   ├── agent/               # LangGraph agent, tools, memory, history store
│   ├── tools/knowledge.py   # Qdrant + Hugging Face ingestion/query utilities
│   ├── main.py              # FastAPI app factory + middleware
│   └── config.py            # Pydantic settings pulled from env
├── scripts/                 # (reserved for automation helpers)
├── tests/                   # Pytest suites
└── README.md                # You are here ✨
```

---

## 🧭 Roadmap Ideas
- [ ] Add automated deployment manifests (Helm/Compose) for the full stack.
- [ ] Provide synthetic data loaders for local development without production credentials.
- [ ] Extend evaluation harness (e.g., RAGAS) for knowledge grounding quality.

---

## 🤝 Contributing
Issues and pull requests are welcome! Please open a discussion with the Populix ML team before major changes. Follow conventional commit messages and ensure the CI suite passes.

Happy building! 💫
