# M14: RAG Architecture (Authoritative Knowledge Layer)

## 1. Objective
M14 introduces a Retrieval-Augmented Generation (RAG) layer to supply **documentary context** from authoritative sources (such as CGWB methodology documents) to the M13 Gemini + LangGraph orchestration layer.

**CRITICAL RULE:**
RAG provides documentary context. It does not replace project-derived groundwater measurements or analytical outputs.

## 2. Architecture & Provenance
The architecture consists of an ingestion pipeline and a retrieval module:
- **Ingestion (`src/rag/ingest.py`)**: Reads a strict manifest (`data/rag/document_manifest.json`), chunks and embeds verified text documents, and stores them in a local index. 
- **Retrieval (`src/rag/retriever.py`)**: Uses dot-product (cosine) similarity over normalized NumPy matrices to fetch the most relevant text chunks.
- **Tools (`src/ai/tools.py`)**: Registers a `document_search` tool mapped to the LangGraph executor.

### Provenance Guarantee
Every document must have its origin, organization, year, and source URL explicitly verified in `data/rag/document_manifest.json` before it is allowed in the production index. **Unverified files are explicitly blocked** from being embedded or retrieved. 
Production RAG documents are sourced from verified official repositories. Derived text extraction is not itself treated as the original source.

## 3. PROJECT DATA EVIDENCE vs DOCUMENTARY EVIDENCE
LangGraph manages two distinct domains of data retrieval:
- **Project Data Evidence**: Fetched by statistical/deterministic APIs (M8.2-D, M10, M11, M12). This represents the actual structural findings of the Groundwater Intelligence Platform.
- **Documentary Evidence**: Fetched by the RAG `document_search` tool. This represents broad definitions, background rules, and methodological context (e.g. "What does CGWB define as Safe extraction?").

The Gemini system prompt enforces clear delineation. Gemini must not generate citations from its internal memory. All document references must be cited clearly to the specific chunk returned by the RAG tool (e.g. `[1] CGWB, "Methodology", 2023`).

## 4. Current Corpus Status

| Document | Organization | Year | Verified | Source |
|---|---|---:|---|---|
| National Compilation on Dynamic Ground Water Resources of India 2023 | Central Ground Water Board (CGWB) | 2023 | True | https://cgwb.gov.in/cgwbpnm/publication-detail/1141 |
| National Water Policy (2012) | Ministry of Water Resources, Government of India | 2012 | True | https://www.jalshakti-dowr.gov.in/static/uploads/2024/02/2023020993.pdf |
| Ground Water Year Book of Maharashtra State 2023-24 | Central Ground Water Board (CGWB) | 2024 | True | https://cgwb.gov.in/cgwbpnm/publication-detail/1687 |

- **Embedding Model**: `models/gemini-embedding-2`
- **Vector Index**: Local JSON + NumPy Array
