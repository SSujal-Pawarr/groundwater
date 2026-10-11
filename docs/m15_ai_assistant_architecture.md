# M15 Groundwater Intelligence AI Assistant Architecture

## Overview
The AI Assistant acts as a conversational interpretation and orchestration layer on top of the deterministic Groundwater Intelligence modules (M1-M14). It leverages the Gemini LLM via LangGraph to route user queries to the appropriate analytical engines, retrieve results, and synthesize a grounded, natural-language response. 

**Key Principle:** The assistant is an interpretation layer. It does NOT generate new scientific models or calculations. It relies strictly on evidence provided by the underlying project tools.

## Architecture
The assistant is integrated into the existing React command-center dashboard and communicates with the backend via a dedicated `POST /api/v1/assistant/chat` endpoint.

- **Frontend:** React component (`AIAssistant.tsx`) providing a collapsible widget, maintaining local message history, and rendering AI responses with embedded source citations and tool execution indicators.
- **Backend API:** FastAPI route (`assistant.py`) handling conversational state matching, site context injection, and delegating to the LangGraph execution engine.
- **LangGraph Orchestrator:** 
  - Parses intent using a routing agent.
  - Dynamically binds and executes tools to gather evidence.
  - Generates a grounded response based on the collected facts.
- **Evidence Providers (Tools):** Existing data access layer (DAL) queries wrapping the M6 Alert Engine, M8.3 Forecast Engine, M10 Drought Intelligence, M11 Flood Potential, M12 Stress Intelligence, and M14 RAG document search.

## Tool Hierarchy
The assistant utilizes a strict set of bounded tools:
1. `groundwater_query`: Fetch raw telemetry.
2. `condition_query`: Fetch condition classification (NORMAL_RANGE, EXTREMELY_LOW, etc.).
3. `alert_query`: Fetch statistical alerts (WARNING, WATCH, etc.).
4. `forecast_query`: Fetch the next-valid-observation persistence forecast.
5. `drought_query`: Fetch M10 groundwater drought intelligence.
6. `flood_potential_query`: Fetch M11 groundwater flood potential.
7. `stress_query`: Fetch M12 groundwater stress.
8. `document_search`: Perform RAG retrieval for methodology and concepts.

## Source Hierarchy
To resolve conflicts and prioritize facts, the system enforces the following hierarchy:
1. **Deterministic Project Tools:** Analytical results from the project's statistical models.
2. **Persisted Project Artifacts:** Database entries for condition, alerts, and metrics.
3. **M14 Authoritative Documents:** RAG text chunks from CGWB and policy documents.
4. **Gemini Reasoning:** LLM synthesis (lowest priority, must not override evidence).

## Conversation Context
Conversations are uniquely identified via a `conversation_id`. The backend maintains a short-term in-memory representation of conversation turns, allowing the LLM to process follow-up questions. Furthermore, when a user selects a site in the frontend map, the `candidate_site_id` is seamlessly injected into the user query context, enabling implicit references (e.g., "What is its status?").

## Error Handling & Rate Limiting
- **Graceful Degradation:** The AI detects and handles `429 Too Many Requests` or quota exhaustion errors from the Gemini API. 
- When an error occurs, the API returns a fallback message: `"AI generation is temporarily unavailable. The deterministic project data is still available."`
- **Ambiguous Queries:** If the user fails to provide a candidate site and asks a site-specific question, the LLM will request clarification.
- **Empty Retrieval:** If tools return no data, the LLM states that there is insufficient project evidence.

## Limitations
- The AI is bound to the available deterministic tool outputs. It cannot interpolate missing data or estimate groundwater metrics outside the established engines.
- State is kept in-memory for testing; in a full production system, conversations would be persisted in a database (e.g., Redis or PostgreSQL).
- Persistence forecasts are strictly available only for the Maharashtra telemetry dataset.
- Drought intelligence requires 10 years of historical data and is unavailable for shorter telemetry spans.
