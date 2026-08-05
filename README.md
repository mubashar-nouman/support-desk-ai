# Support Desk AI

An AI customer-service application powered by Google Gemini. Administrators upload support documents into a local knowledge base, and customers use a chat interface to ask questions grounded in those documents.

## Features

- Google Gemini support through the unified LLM client
- Single-screen workspace: upload a document and it opens side by side with the chat
- Resizable split view with an in-document search (highlighting and match navigation)
- Multi-file upload for TXT, Markdown, CSV, JSON, LOG, and PDF files
- Answers grounded in the document you are reading, with the source file cited
- Semantic retrieval via Gemini embeddings stored in a local ChromaDB index
- FastAPI backend and interactive Swagger documentation
- Local file storage in `data/knowledge_base`

## Setup with Conda

```bash
conda create -n ai-customer-service python=3.11 -y
conda activate ai-customer-service
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set:

```env
LLM__PROVIDER=gemini
LLM__GEMINI__API_KEY=your_gemini_api_key
LLM__GEMINI__MODEL=gemini-2.5-flash
```

Validate configuration:

```bash
python scripts/validate_config.py
```

## Run the application

```bash
python main.py
```

Open the app:

- Workspace: http://localhost:8000
- API documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/health

The app opens on an upload screen. Drop in a document and it is indexed, then the
screen becomes a split workspace with the document on the left and the assistant on
the right. Use **Add document** in the top bar to upload more, switch between them,
or remove them. (`/admin` and `/chat` both redirect to the workspace.)

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check application status |
| GET | `/knowledge/status` | List indexed documents |
| POST | `/knowledge/upload` | Upload and index a document |
| GET | `/knowledge/document/{filename}` | Extracted text of a document, for the viewer |
| DELETE | `/knowledge/document/{filename}` | Remove a document and its vectors |
| POST | `/chat` | Generate a grounded answer (`active_file` prioritises the open document) |

## Tests

```bash
python -m pytest
python scripts/validate_models.py
```

## Project structure

```text
config/                 Application settings and prompts
data/knowledge_base/    Uploaded support documents
data/chroma/            Local vector index
src/api/                FastAPI app
src/api/static/         Single-page workspace (index.html, app.js, styles.css)
src/llm/                Provider abstraction and Gemini integration
src/models/             Domain models
tests/                  Unit and integration tests
```

## Notes

Retrieval uses Gemini embeddings stored in a local ChromaDB index. Each paragraph of
an uploaded file costs one embedding call, so large PDFs take a moment to index and
can hit free-tier rate limits.

PostgreSQL and Redis settings are included for future production extensions; the
upload and chat workflow does not require those services to be running.
