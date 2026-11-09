<p align="center"><img src="assets/logo_small.png" alt="STRENTOR: Break. Build. Become." width="200"></p>

# STRENTOR Assistant: RAG + Agents + Lead Capture

Upload documents, ask questions, get grounded, cited answers from four cooperating agents (Planner, Retriever, Reasoner, Validator). A Generative AI capstone, built for the STRENTOR business (strentor.com). No API key, account or contact with the author is needed to evaluate it.

## Start here: open the live app (nothing to install)

**https://strentor-assistant.streamlit.app/**

- The chat opens straight away. Click an example question.
- To unlock uploads, agent traces, leads and the self-test, type the team password **`evaluator`** in the sidebar.
- If the page says the app is asleep, click **"Yes, get this app back up!"** and wait about a minute (free hosting sleeps when idle).
- Then follow the **Five-minute tour** below.

## Backup only: run it on your own computer

Use this only if the live link is unavailable. It needs Python 3.9 or newer and internet on the first run (a small embedding model, about 80 MB, downloads once).

| System | Do this |
|---|---|
| **Mac / Linux** | In this folder run `./run.sh` (if "permission denied": `chmod +x run.sh`) |
| **Windows** | Double-click `run.bat` |
| **Docker** (no Python needed) | `docker build -t strentor-assistant .` then `docker run -p 8501:8501 strentor-assistant` |

Opens at **http://localhost:8501**; the team password is again **`evaluator`**. The local app runs offline in "extractive" mode (answers are cited sentences from the documents); the same four agents, guardrails and tests apply.

Generated (LLM) answers are optional. Evidence from a real Ollama run is in `docs/screenshots/`, and the owner's setup notes (deployment, free Gemini/Groq key, keep-alive) are in `docs/DOCUMENTATION.md`, section 4, for reference only.

## Five-minute tour (works on the live app or locally)

1. **Chat tab**: click the example questions (retrieval with sources, multi-part question, medical redirect, injection block, out-of-scope).
2. **Sidebar > team password**, then click **Load sample documents**. The four demo files (TXT, CSV, Excel, PDF) are already in `sample_docs/` inside this folder and are indexed for you; nothing to copy or download.
3. Ask *"Which languages are available in India?"* (Excel), *"How is a corporate program designed?"* (PDF), *"What equipment is needed?"* (TXT). More in [`docs/SAMPLE_QUESTIONS.md`](docs/SAMPLE_QUESTIONS.md).
4. Open **Agent trace** under any answer: plan, tool calls, timings, grounding verdict.
5. **Self-test tab > Run self-test**: 14 live checks.
6. **Upload your own file**, tag it *internal* or *public*. Internal content is invisible in client mode (use a private window without the password to confirm).
   **Or ingest a web page** (needs internet): paste `https://www.strentor.com` into *Or add a page URL*, click **Ingest URL**, then ask *"How many regions does STRENTOR offer priced coaching in?"* (expected: 89, source `www.strentor.com`). URL pages are indexed as public. Other server-rendered pages work too; pages that need JavaScript to show their text cannot be read.
7. **Talk to Aditya** form (bottom of the sidebar): submit a test lead, then see it in the **Leads** tab and `leads/leads.csv`.
8. **Evaluator guide tab**: architecture diagram and task map.

Run the 45 automated tests (offline, about ten seconds): `python -m unittest discover -s tests -v`

## Demo and verification

- **2.5-minute narrated screen demo (recorded in extractive mode; generated answers from a real local Ollama run are in `docs/screenshots/`):** [`docs/demo.mp4`](docs/demo.mp4) walks through client mode, guardrails, team mode, sample files, agent trace, self-test and the lead form. It was recorded in the offline test setup (extractive mode, stand-in embeddings), so wording of answers will differ slightly from a fresh run with the real embedding model.
- **Tests:** on 9 Nov 2026, all 45 automated tests passed on Python 3.9.25 and on Python 3.13 (command below), and the 14 live checks of the in-app Self-test tab passed (offline stand-in embeddings). Please also run the Self-test tab once on your machine; it exercises the real embedding model.

## Documentation

| Open | For |
|---|---|
| [`docs/DOCUMENTATION.pdf`](docs/DOCUMENTATION.pdf) (source: [`.md`](docs/DOCUMENTATION.md)) | Concepts, setup, architecture, workflow, agent roles, safety, testing, deployment, design decisions, limitations, challenges, likely viva questions |
| [`docs/TASK_MAP.md`](docs/TASK_MAP.md) | Each of the 10 capstone tasks, where it lives in the code, and a one-minute check (also shown inside the app) |
| [`docs/SAMPLE_QUESTIONS.md`](docs/SAMPLE_QUESTIONS.md) | Test questions per sample file with expected results |

## Project structure

```
README.md               This file: run, tour, structure, troubleshooting
app.py                  Streamlit interface (Chat, Evaluator guide, Leads, Self-test)
src/
  config.py             All settings
  ingestion.py          Validate, parse (PDF/TXT/MD/CSV/Excel/URL), chunk
  vectorstore.py        ChromaDB store, similarity search, public/internal filter
  rag.py                LLM backends (Ollama, Gemini/Groq, Claude), grounding prompt, extractive answers
  agents.py             Planner, Retriever, Reasoner, Validator + tool-call trace
  guardrails.py         Input checks, prompt-injection filter, medical redirect
  leads.py              Lead validation and CSV storage
  service.py            Entry points used by the UI; logging and error handling
  selftest.py           The live self-test
  theme.py              STRENTOR colours, font and logo
tests/                  Logic tests (test_core.py) and headless UI tests (test_ui.py)
docs/                   DOCUMENTATION (.md, .pdf), TASK_MAP, SAMPLE_QUESTIONS, architecture.png, demo.mp4
assets/                 Official STRENTOR logo files
sample_docs/            Demo files (TXT, CSV, XLSX, PDF), labelled as sample data
data/kb/                Public STRENTOR knowledge base loaded at start-up
scripts/                warmup.py (model download), make_diagram.py, make_pdfs.py
Dockerfile, run.sh, run.bat, requirements.txt, .env.example
```

## Troubleshooting

| Problem | Fix |
|---|---|
| First start is slow | It is downloading the embedding model once; later starts take seconds |
| "Could not load the public knowledge base" or a connection error | No internet on first run. Connect, then restart. After the one-time download it works offline |
| `.env` not visible | Hidden file (starts with a dot); the script creates it. On Mac press Cmd+Shift+. in Finder |
| `permission denied: ./run.sh` | `chmod +x run.sh` |
| Port 8501 in use | `streamlit run app.py --server.port 8502` (activate `.venv` first) |
| Team password rejected | Check `TEAM_PASSWORD` in `.env`; restart after editing |
| Clean slate | Stop the app and delete `chroma_db/`; it is rebuilt at next start |

## Scope notes

- The live app runs on Streamlit Community Cloud (deployment steps in `docs/DOCUMENTATION.md` section 11); the Docker image is the alternative.
- `sample_docs/` holds fictional demo content, labelled as such. `data/kb/strentor_public.md` summarises the public strentor.com site.
- Extractive mode returns cited sentences, not fluent prose. The keyword guardrails are not exhaustive (see Limitations in the documentation).


**Live app availability:** the free Streamlit tier sleeps when idle. `.github/workflows/keep-alive.yml` visits the app every 6 hours to keep it awake. If you still see "Yes, get this app back up!", click it and wait about 30 seconds.
