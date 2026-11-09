## Capstone task map: where each requirement lives and how to verify it

Open the app, enter the team password (default `evaluator`), and use the **Self-test** tab for a live check of most rows below.

| # | Brief asks for | Implemented in | Verify in under a minute |
|---|---|---|---|
| 1 | Project foundation: repo, environment config, app structure | `app.py`, `src/` package, `requirements.txt`, `.env.example`, `run.sh`, `run.bat`, `Dockerfile`, `src/config.py` | Run `./run.sh` (Mac/Linux) or `run.bat` (Windows). One command installs and starts everything |
| 2 | Interface to upload documents and ask questions | `app.py` (Streamlit): chat, example-question buttons, uploader, lead form | Click an example question in the **Chat** tab; upload files in the sidebar (team mode) |
| 3 | Ingest PDF, TXT, CSV, Excel | `src/ingestion.py`: `load_file`, `validate_file`, `load_url` (also Markdown and web pages) | Team mode > **Load sample documents** (loads one TXT, CSV, XLSX and PDF). Sidebar then lists each file |
| 4 | Chunk content for retrieval | `src/ingestion.py`: `chunk_records` (1000 characters, 150 overlap, paragraph/sentence-aware; Excel sheets and PDF pages keep their labels) | Self-test: "Chunking respects size limit". Unit test `test_chunks_are_bounded_and_overlap` |
| 5 | Embeddings stored in a vector database | `src/vectorstore.py`: ChromaDB, local MiniLM embeddings, metadata (source, page, visibility) | Sidebar "Indexed:" list; Self-test: "Vector store has content" |
| 6 | Similarity-search retrieval | `src/vectorstore.py: search`, `src/agents.py: retriever` (multi-query, dedupe, rank) | Ask any question in team mode, open **Agent trace**: see `search_documents` calls and hit counts |
| 7 | RAG pipeline: retrieved context + LLM, grounded answers | `src/rag.py` (grounding prompt, citations, `NOT_FOUND` rule; Ollama, Claude, or extractive mode) | Every answer lists **Sources** with file and page. Ask "Who won the cricket world cup?" to see the safe "not on file" reply |
| 8 | Agents that plan, retrieve, reason, respond using tools | `src/agents.py`: Planner, Retriever, Reasoner, Validator; tools `search_documents`, `check_grounding` | Ask "How long is the Flagship programme and who is it for?" in team mode: the trace shows the plan split into 3 sub-queries, tool calls, timings and the validation result |
| 9 | Error handling, input validation, guardrails against hallucination and unsafe output | `src/guardrails.py`, `src/agents.py` (validator, retry, fallback), `src/service.py` (error handling, logging), `src/leads.py` | **Self-test** tab (14 live checks). Try the red-flag examples: medical question, prompt injection. Terminal: `python -m unittest discover -s tests -v` (29 tests) |
| 10 | Deploy and document | `docs/DOCUMENTATION.md` / `.pdf`, `docs/architecture.png`, `Dockerfile`, Streamlit Cloud steps (documentation section 11) | Read `docs/DOCUMENTATION.md`; optionally `docker build -t strentor-assistant . && docker run -p 8501:8501 strentor-assistant` |

### Beyond the brief
- **Lead capture** to `leads/leads.csv` with consent, validation and CSV-injection protection (business feature for strentor.com).
- **Two audiences**: client mode only ever retrieves `public` chunks (enforced in the vector query), team mode also sees `internal` chunks.
- **Runs with no API key**: without a local LLM, the same four agents run in extractive mode (rule-based plan, verbatim cited sentences, sentence-level grounding check).
