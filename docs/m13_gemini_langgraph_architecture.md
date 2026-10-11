# M13: Gemini & LangGraph AI Orchestration Layer

## Architecture

The AI layer serves as an **interface and orchestration layer** to interact with the project's analytical modules. It is explicitly **NOT** the scientific source of truth. 

**Data Flow:**
```
User Query 
    ↓ 
FastAPI Endpoint (/api/v1/assistant/query)
    ↓ 
LangGraph (AgentState)
    ↓
Query Interpretation (Gemini)
    ↓
Tool Selection & Execution (GroundwaterDAL)
    ↓
Evidence Collection (Structured Data)
    ↓
Response Generation (Gemini)
    ↓ 
Grounded Answer
```

## Gemini's Role
Gemini is used as a language-generation and reasoning interface over project-provided evidence. It is not the scientific source of truth. 

All groundwater values, conditions, alerts, forecasts, drought intelligence, flood potential, and stress intelligence originate from project data and deterministic/model-based project components rather than from Gemini's internal knowledge.

## LangGraph Role
LangGraph manages the orchestration workflow (`AgentState`). It strictly routes queries to tools, executes those tools to fetch actual project evidence, appends the evidence back into the state, and passes the context back to Gemini to formulate a natural language response.

## Tool Layer
We implemented the following tools mapping directly to `GroundwaterDAL` queries:
1. `groundwater_query`: Retrieves raw telemetry observations.
2. `condition_query`: Retrieves M8.2-D condition states.
3. `alert_query`: Retrieves M6 statistical early warnings.
4. `forecast_query`: Retrieves M8.3 persistence forecasts.
5. `drought_query`: Retrieves M10 drought intelligence.
6. `flood_potential_query`: Retrieves M11 flood potential intelligence.
7. `stress_query`: Retrieves M12 stress intelligence.

## Security & Environment Variables
- `MY_GRW_API_KEY`: The Gemini API key, loaded via `dotenv` from `.env`.
- `GEMINI_MODEL`: Model configuration (defaults to `gemini-1.5-flash`).
- **Secret Hygiene**: The API key is restricted exclusively to the backend. It is never logged, exposed via APIs, printed, or sent to the frontend.
- **Dependency Scope**: Only standard LangChain and LangGraph dependencies (`langchain-core`, `langgraph`, `langchain-google-genai`) were added.

## Supported Intents
- `TOOL_ROUTING`: Invoked when the agent resolves a candidate site ID and accurately triggers a data tool.
- `DIRECT_ANSWER`: Used when the tool cannot satisfy the request, the query is unsupported, or Gemini falls back to gracefully explaining project limitations.
- `ERROR`: Used when the tool execution or the LLM integration encounters an unexpected failure.

## Hallucination Controls
1. **Tool-First Principle**: Gemini cannot invent responses; it exclusively relies on structured evidence pulled by tools.
2. **Scientific Terminology Guardrails**: The prompt strictly enforces terminology (e.g., M10 is "GROUNDWATER DROUGHT INTELLIGENCE", M12 is "GROUNDWATER STRESS INTELLIGENCE").
3. **No Inference of Causality**: Gemini is instructed not to assume causality or extrapolate conditions like "flood" from generic high water levels without explicit tool corroboration.

## Failure Handling
- **Missing API Key**: Falls back to HTTP 500 without exposing the key, handled safely during module loading.
- **Unavailable Data**: If tools return no data, the LLM responds that "the available project data does not support the requested conclusion."
- **Unsupported Queries**: Ambiguous or futuristic queries (e.g., "Which village will run out of water?") are explicitly rejected by the LLM based on system prompt rules.

## Future RAG Integration
This milestone implements the foundation for AI interaction. Retrieval-Augmented Generation (RAG) using vector databases, PDF document parsing, and broader project knowledge answering is deferred to future milestones.
