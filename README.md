# 🌌 Orion — Populix Knowledge Agent API

Welcome to **Orion**, a FastAPI-based backend that fulfills the "Machine Learning Engineer Technical Assignment" brief by exposing a minimal yet production-minded API for interacting with an LLM-powered agent. The agent is fine-tuned (via prompt + tools) to answer questions about **Populix**—from business model insights to product capabilities—by grounding its responses in a curated knowledge base.

### ☁️ Production Deployment

Orion is live on **Google Cloud Run**. Explore the public Swagger UI at [https://orion-53063754153.asia-southeast2.run.app/docs](https://orion-53063754153.asia-southeast2.run.app/docs) and click **Authorize**, supplying the `TOKEN` shared via email to access the protected endpoints.

> ⚠️ **Note:** The first access might take a little longer to respond because Orion is deployed with Cloud Run’s *request-balanced* system.  
> This means the deployment automatically **scales down to zero** when idle and **warms up again** upon new requests.

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

### 🧩 Knowledge Ingestion Flow

<p align="center">
  <img src="docs/assets/populix-ingest.png" alt="Ingest Document" width="720" />
</p>

1. **Client Upload Trigger** — A client sends a request to the `/upload-link` endpoint to register a new knowledge source.
2. **Web Crawling** — Orion fetches and crawls the referenced webpage, capturing its contents as raw text.
3. **LLM Cleaning (Qwen 3 32B)** — The raw text is normalized and rewritten by the Qwen 3 32B model so the content is structured and easy to chunk.
4. **Chunking** — The polished text is segmented into retrieval-friendly chunks.
5. **Vector Store Insertion** — Each chunk is embedded and persisted into the Qdrant vector database to make it searchable for the agent.

> 🗒️ **Knowledge Sources Uploaded to Date**
>
> - https://info.populix.co/
> - https://info.populix.co/solutions/market-research
> - https://info.populix.co/solutions/policy-society-research
> - https://info.populix.co/insight-hub
> - https://info.populix.co/solutions/popsurvey
> - https://info.populix.co/solutions/respondent-only
> - https://info.populix.co/industries
> - https://info.populix.co/industries/automotive
> - https://info.populix.co/industries/venture-capital-and-investments
> - https://info.populix.co/industries/fast-moving-consumer-goods
> - https://info.populix.co/industries/professional-services
> - https://info.populix.co/industries/information-and-computer-technology
> - https://info.populix.co/industries/banking
> - https://info.populix.co/industries/goverment-institutions
> - https://info.populix.co/industries/non-profit-organizations
> - https://info.populix.co/industries/political-organizations
> - https://info.populix.co/industries/media-communications
> - https://info.populix.co/data-hub
> - https://info.populix.co/panel
> - https://info.populix.co/articles/faq/
> - https://info.populix.co/indonesia-masters-university-rankings

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
# Replace http://localhost:8000 with https://orion-53063754153.asia-southeast2.run.app if you want to call the public Cloud Run deployment.
curl -X POST http://localhost:8000/v1/agent/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "input": "Apa saja produk riset Populix untuk brand FMCG?",
        "session_id": "demo-session",
        "user_id": "demo-user"
      }'
```

**Request fields**

| Field | Type | Description |
|-------|------|-------------|
| `input` | `string` | Natural-language question that the agent should answer. |
| `session_id` | `string` | Conversation identifier so follow-up questions reuse previous context. |
| `user_id` | `string` | Unique identifier for the caller; partitions history storage per user. |

#### Generate Response Example
```json
{
  "answer": "Hai Sobat, Populix menawarkan berbagai produk dan layanan untuk kebutuhan riset pasar dan sosial, antara lain:\n\n1. **PopSurvey**  \n   Platform survei *self-service* untuk membuat dan menjalankan survei secara mandiri dengan mudah.\n\n2. **Market Research Solutions**  \n   - **Customer Experience**: Analisis NPS, studi kepuasan pelanggan.  \n   - **Brand Research**: Pemetaan persepsi, kesehatan merek, dan posisi pasar.  \n   - **Product Research**: Uji konsep, pengujian produk, dan segmentasi pasar.  \n   - **Market Overview**: Analisis tren industri dan peluang pasar.\n\n3. **Solutions Berdasarkan Industri**  \n   - **FMCG**: Studi perilaku konsumen, inovasi produk, dan strategi pemasaran.  \n   - **Professional Services**: Pemantauan kesehatan merek dan strategi akuisisi klien.  \n   - **ICT & FinTech**: Analisis adopsi teknologi dan kebutuhan pasar.  \n   - **Banking**: Penelitian pola penggunaan layanan keuangan.\n\n4. **Data Hub & Panel**  \n   Akses ke basis data responden yang luas di Indonesia untuk menjangkau target audiens secara akurat.\n\n5. **Layanan Khusus**  \n   - Bantuan pengembangan kuesioner.  \n   - Analisis data dan pelaporan mendalam.  \n\nUntuk detail lebih lanjut, kunjungi [situs resmi Populix](https://info.populix.co/). Semoga bermanfaat! 😊",
  "session_id": "demo-session",
  "latency_ms": 11060
}
```

**Response fields**

| Field | Type | Description |
|-------|------|-------------|
| `answer` | `string` | Model-generated response grounded in the Populix knowledge base. |
| `session_id` | `string` | Echoes the conversation identifier supplied in the request. |
| `latency_ms` | `number` | End-to-end processing time in milliseconds for the request. |

#### History Request Example
```bash
TOKEN="<your-api-token>"
# Replace http://localhost:8000 with https://orion-53063754153.asia-southeast2.run.app if you want to call the public Cloud Run deployment.
curl -G http://localhost:8000/v1/agent/history \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode "user_id=demo-user" \
  --data-urlencode "session_id=demo-session" \
  --data-urlencode "order=DESC" \
  --data-urlencode "offset=0" \
  --data-urlencode "limit=20"
```

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | `string` | Required identifier of the user whose chat history to fetch. |
| `session_id` | `string` | Required conversation thread within the user's history. |
| `order` | `"ASC" \| "DESC"` | Sort direction for the results; defaults to newest first (`DESC`). |
| `offset` | `number` | Number of records to skip for pagination; defaults to `0`. |
| `limit` | `number` | Maximum number of history entries to return; defaults to `20`. |

#### History Response Example

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

**Response fields**

| Field | Type | Description |
|-------|------|-------------|
| `histories` | `object[]` | Array of prior question/answer pairs for the requested user and session. Each entry has the fields below. |

**History entry object**

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | `string` | User identifier associated with the conversation turn. |
| `session_id` | `string` | Session identifier grouping the turn into a chat thread. |
| `input` | `string` | Original user question captured for that turn. |
| `answer` | `string` | Agent response that was returned for the question. |
| `created_at` | `string \| null` | ISO 8601 timestamp when the turn was stored (may be `null` if unavailable). |

### Knowledge Service (`/v1/knowledge`)
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Liveness probe for the knowledge ingestor. |
| `POST` | `/upload-link` | Deduplicates and ingests new Populix web pages. Stores chunks in Qdrant and embeddings on Hugging Face. |

#### Upload Request Example
```bash
TOKEN="<your-api-token>"
# Replace http://localhost:8000 with https://orion-53063754153.asia-southeast2.run.app if you want to call the public Cloud Run deployment.
curl -X POST http://localhost:8000/v1/knowledge/upload-link \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "links": [
          "https://info.populix.co/",
          "https://info.populix.co/solutions/market-research",
          "https://info.populix.co/solutions/policy-society-research",
          "https://info.populix.co/insight-hub"
        ]
      }'
```

#### Upload Response Example
```json
{
  "skipped": [
    "https://info.populix.co/"
  ],
  "processed": [
    "https://info.populix.co/solutions/market-research",
    "https://info.populix.co/solutions/policy-society-research",
    "https://info.populix.co/insight-hub"
  ],
  "counts": {
    "skipped": 1,
    "processed": 3,
    "total_input": 4,
    "total_unique": 4
  }
}
```

**Request fields**

| Field | Type | Description |
|-------|------|-------------|
| `links` | `string[]` | Array of absolute URLs to ingest. Duplicates are automatically removed before processing. |

#### Upload Response Example
```json
{
  "skipped": [
    "https://info.populix.co/"
  ],
  "processed": [
    "https://info.populix.co/solutions/market-research",
    "https://info.populix.co/solutions/policy-society-research",
    "https://info.populix.co/insight-hub"
  ],
  "counts": {
    "skipped": 1,
    "processed": 3,
    "total_input": 4,
    "total_unique": 4
  }
}
```

**Response fields**

| Field | Type | Description |
|-------|------|-------------|
| `skipped` | `string[]` | Links that were already present in Qdrant and therefore not reprocessed. |
| `processed` | `string[]` | Newly ingested links that completed crawling, cleaning, chunking, and embedding. |
| `counts` | `object` | Summary of how many links were skipped or processed. Contains the keys below. |

**`counts` object**

| Field | Type | Description |
|-------|------|-------------|
| `skipped` | `number` | Count of links returned in the top-level `skipped` array. |
| `processed` | `number` | Count of links returned in the top-level `processed` array. |
| `total_input` | `number` | Total number of links received in the original request payload (including duplicates). |
| `total_unique` | `number` | Number of distinct links evaluated after duplicate removal. |

## 🗂️ Project Structure
```
orion/
├── .github/
│   └── workflows/           # CI configuration for linting, testing, and deploys
├── dockerfile               # Container image definition for Cloud Run
├── docs/
│   └── assets/              # Architecture & process diagrams
├── orion/
│   ├── __init__.py
│   ├── agent/               # LangGraph agent, state, and tool orchestration
│   ├── api/                 # FastAPI routers, dependencies, and auth
│   ├── config.py            # Pydantic settings pulled from the environment
│   ├── main.py              # FastAPI application factory & middleware
│   └── tools/               # Knowledge ingestion/query utilities
├── pyproject.toml           # Poetry/PEP 621 metadata, dependencies, and tooling config
├── scripts/                 # Helper scripts (e.g., init.sh for local setup)
├── tests/                   # Pytest-based API & ingestion tests
└── README.md                # You are here ✨
```

---

## 🤝 Contributing
Issues and pull requests are welcome!

Happy building! 💫
