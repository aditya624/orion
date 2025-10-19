# 🌌 Orion — Populix Knowledge Agent API

Welcome to **Orion**, a FastAPI-based backend that fulfills the "Machine Learning Engineer Technical Assignment" brief by exposing a minimal yet production-minded API for interacting with an LLM-powered agent. The agent is fine-tuned (via prompt + tools) to answer questions about **Populix**—from business model insights to product capabilities—by grounding its responses in a curated knowledge base.

### ☁️ Production Deployment

Orion is live on **Google Cloud Run**. Explore the public Swagger UI at [https://orion-53063754153.asia-southeast2.run.app/docs](https://orion-53063754153.asia-southeast2.run.app/docs) and click **Authorize**, supplying the `TOKEN` shared via email to access the protected endpoints.

### 🔄 Development-to-Production Flow

<p align="center">
  <img src="docs/assets/populix-development-process.png" alt="Development to production workflow showing development, GitHub, CI, Docker Hub, Cloud Run, Secret Manager, and Public API" width="820" />
</p>

This flow illustrates how changes ship safely to users:

1. **Development Process** — Features are planned, implemented, and reviewed locally before opening a pull request.
2. **Push / Merge to GitHub** — Once approved, the merge triggers the CI pipeline on the hosted repository.
3. **CI: Test · Build · Push** — Automated checks run, the Docker image is built, and the artifact is pushed to Docker Hub.
4. **Docker Hub Registry** — Serves as the immutable source for runtime images consumed in production.
5. **Cloud Run Deployment** — The latest image is pulled and rolled out on Google Cloud Run, wired to the public API endpoint.
6. **Secret Manager** — Managed secrets (TOKEN, database keys, Langfuse keys, etc.) are injected as environment variables during deployment.

---

## 🎯 Assignment Alignment
| Requirement | How Orion Delivers |
|-------------|--------------------|
| Build a functional API service on top of an open-source LLM | Uses `langchain` with the **Groq-hosted Qwen 3 32B** chat model plus tool bindings. |
| Provide a public API endpoint that exposes the model's reasoning ability | `/v1/agent/generate` handles authenticated question answering with retrieval augmentation. |
| Run locally or on cloud infrastructure | Runs with `uvicorn` locally or via Docker; relies on managed services (MongoDB, Qdrant, Langfuse) but can be substituted with self-hosted instances. |

---

## 🧠 High-Level Architecture Production Ready

<p align="center">
  <img src="docs/assets/populix-architecture-production.png" alt="Populix agent architecture diagram showing Orion orchestrating Groq Qwen 3 32B, Qdrant, MongoDB, Langfuse, and Hugging Face" width="720" />
</p>

### Component Responsibilities

| Component | Role in the Populix Agent |
|-----------|---------------------------|
| **Clients** | Populix web / internal tools send authenticated questions to Orion. |
| **Orion Service** | FastAPI handles HTTP, validates bearer tokens, and forwards work to the LangChain/LangGraph agent that chooses between retrieval, memory, and generation tools. |
| **Hugging Face Endpoint Embeddings** | Produces dense vectors for new Populix documents during ingestion. |
| **Qdrant Vector DB** | Stores embeddings and supports semantic search to supply the agent with grounded Populix knowledge. |
| **MongoDB Chat History** | Maintains per-user conversation state so follow-up questions inherit prior context. |
| **Langfuse Observability** | Tracks prompts, traces, and evaluation metrics for debugging and governance. |
| **Groq + Qwen 3 32B** | Groq's accelerated inference host runs the open-source Qwen 3 32B model that ultimately drafts the natural-language answer. |

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
Create a `.env` file (or export variables) with only the required secrets (all sensitive keys have been shared with you via email):

```env
MONGODB_URI=<mongodb-uri>
GROQ_API_KEY=<groq-api-key>
QDRANT_API_KEY=<qdrant-api-key>
HF_TOKEN=<hf-inference-token>
LANGFUSE_SECRET_KEY=<langfuse-secret-key>
LANGFUSE_PUBLIC_KEY=<langfuse-public-key>
LANGFUSE_HOST="https://cloud.langfuse.com"
TOKEN=<api-token>
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

#### Generate Response Example
```json
{
  "answer": "Hai Sobat, Populix menawarkan berbagai produk dan layanan untuk kebutuhan riset pasar dan sosial, antara lain:\n\n1. **PopSurvey**  \n   Platform survei *self-service* untuk membuat dan menjalankan survei secara mandiri dengan mudah.\n\n2. **Market Research Solutions**  \n   - **Customer Experience**: Analisis NPS, studi kepuasan pelanggan.  \n   - **Brand Research**: Pemetaan persepsi, kesehatan merek, dan posisi pasar.  \n   - **Product Research**: Uji konsep, pengujian produk, dan segmentasi pasar.  \n   - **Market Overview**: Analisis tren industri dan peluang pasar.\n\n3. **Solutions Berdasarkan Industri**  \n   - **FMCG**: Studi perilaku konsumen, inovasi produk, dan strategi pemasaran.  \n   - **Professional Services**: Pemantauan kesehatan merek dan strategi akuisisi klien.  \n   - **ICT & FinTech**: Analisis adopsi teknologi dan kebutuhan pasar.  \n   - **Banking**: Penelitian pola penggunaan layanan keuangan.\n\n4. **Data Hub & Panel**  \n   Akses ke basis data responden yang luas di Indonesia untuk menjangkau target audiens secara akurat.\n\n5. **Layanan Khusus**  \n   - Bantuan pengembangan kuesioner.  \n   - Analisis data dan pelaporan mendalam.  \n\nUntuk detail lebih lanjut, kunjungi [situs resmi Populix](https://info.populix.co/). Semoga bermanfaat! 😊",
  "session_id": "demo-session",
  "latency_ms": 11060
}
```

#### History Request Example
```bash
TOKEN="<your-api-token>"
curl -G http://localhost:8000/v1/agent/history \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode "user_id=demo-user" \
  --data-urlencode "session_id=demo-session" \
  --data-urlencode "order=DESC" \
  --data-urlencode "offset=0" \
  --data-urlencode "limit=20"
```

#### History Response Example

> Gunakan parameter `offset` (default: 0) dan `limit` (default: 20) untuk melakukan pagination pada riwayat percakapan.

```json
{
  "histories": [
    {
      "user_id": "demo-user",
      "session_id": "demo-session",
      "input": "Halo berikan apa saja product populix!",
      "answer": "Hai Sobat, Populix menawarkan berbagai produk dan layanan untuk kebutuhan riset pasar dan sosial, antara lain:\n\n1. **PopSurvey**  \n   Platform survei *self-service* untuk membuat dan menjalankan survei secara mandiri dengan mudah.\n\n2. **Market Research Solutions**  \n   - **Customer Experience**: Analisis NPS, studi kepuasan pelanggan.  \n   - **Brand Research**: Pemetaan persepsi, kesehatan merek, dan posisi pasar.  \n   - **Product Research**: Uji konsep, pengujian produk, dan segmentasi pasar.  \n   - **Market Overview**: Analisis tren industri dan peluang pasar.\n\n3. **Solutions Berdasarkan Industri**  \n   - **FMCG**: Studi perilaku konsumen, inovasi produk, dan strategi pemasaran.  \n   - **Professional Services**: Pemantauan kesehatan merek dan strategi akuisisi klien.  \n   - **ICT & FinTech**: Analisis adopsi teknologi dan kebutuhan pasar.  \n   - **Banking**: Penelitian pola penggunaan layanan keuangan.\n\n4. **Data Hub & Panel**  \n   Akses ke basis data responden yang luas di Indonesia untuk menjangkau target audiens secara akurat.\n\n5. **Layanan Khusus**  \n   - Bantuan pengembangan kuesioner.  \n   - Analisis data dan pelaporan mendalam.  \n\nUntuk detail lebih lanjut, kunjungi [situs resmi Populix](https://info.populix.co/). Semoga bermanfaat! 😊",
      "created_at": "2025-10-19T09:02:18.446000"
    }
  ]
}
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

## 🤝 Contributing
Issues and pull requests are welcome!

Happy building! 💫
