# Support Ops Environment — Complete Project Documentation

This document describes EVERY file, feature, and implementation detail of the **customer-support-openenv** project — an OpenEnv-compliant reinforcement learning environment simulating real-world SaaS customer support operations.

---

## Project Architecture Overview

```text
customer-support-openenv/
├── models.py                          # Type-safe Pydantic data contracts
├── client.py                          # HTTP + WebSocket client for the environment
├── inference.py                       # Mandatory baseline inference script
├── ticket_generator.py                # 4-Layer Simulation Engine (ticket factory)
├── test_grader.py                     # Perfect-episode validation tests
├── openenv.yaml                       # OpenEnv descriptor
├── pyproject.toml                     # Project config + dependencies
├── Dockerfile                         # Container deployment
├── .dockerignore                      # Docker build exclusions
├── .env                               # Local env vars (HF_TOKEN) — NOT committed
├── .gitignore                         # Git exclusions
├── server/
│   ├── app.py                         # FastAPI server (HTTP + WebSocket endpoints)
│   ├── support_ops_env_environment.py # Core RL environment logic
│   ├── graders/
│   │   └── grader.py                  # 3 task-specific grading functions
│   ├── tasks/
│   │   └── task_data.py               # Task definitions linking to the ticket generator
│   └── tools/
│       └── mock_tools.py              # Simulated account/incident lookup tools
└── agent/
    └── agent.py                       # Baseline agent (rule-based + LLM fallback)
```

The project follows the **OpenEnv 3-component pattern**:
1. **`models.py`** — Type-safe data contracts (what goes in, what comes out)
2. **`server/`** — Environment logic running as a FastAPI microservice
3. **`client.py`** — Python client that abstracts HTTP/WebSocket communication

---

## File-by-File Breakdown

---

### `models.py` — The Data Contract

Defines all Pydantic models used across server, client, and agent.

**`SupportOpsAction`** — What the agent sends each step:
- `action_type`: One of `categorize`, `set_priority`, `route`, `resolve`, `merge_duplicate`, `lookup_account`, `check_incident`, `submit`
- `ticket_id`: Target ticket
- `category`: billing / auth / bug / feature / logistics / incident
- `priority`: urgent / high / medium / low
- `queue`: finance / tech / engineering / product / operations
- `duplicate_ticket_id`: Parent ticket ID (for merge_duplicate)
- `account_id`: For lookup_account tool
- `incident_id`: For check_incident tool

**`SupportOpsObservation`** — What the agent sees:
- `tickets`: List of `Ticket` objects (ticket_id, text, category, priority, queue, status)
- `step_count`: Current step number
- `max_steps`: Episode length limit
- `tool_credits_remaining`: Budget for tool calls
- `queue_health`: Float [0,1] representing global queue state
- `visible_churn_risk`: Dict mapping ticket_id → churn probability

**`SupportOpsState`** — Full internal state (not visible to agent):
- All observation fields plus: `categorized`, `prioritized`, `routed` dicts tracking agent decisions
- `resolved_tickets`, `churn_risk`, `duplicates`, `active_incidents`, `last_tool_result`

**`Ticket`** — Individual support ticket:
- `ticket_id`, `text`, `category`, `priority`, `queue`, `status` (open/resolved)

---

### `ticket_generator.py` — 4-Layer Simulation Engine

This is the deterministic factory generating reproducible episodes mimicking real-world complexity. It uses 4 layers:

1. **Scenario Layer**: Decides global structure (ticket count). Based on difficulty, injects:
   - *Incidents*: Groups multiple tickets under one incident ID (e.g., `INC123`)
   - *Duplicates*: Modifies tickets to share context and flags
   - *Hidden Flags*: VIP, Fraud, Churn probabilities
2. **Text Layer**: Provides a baseline language structure mapping to 6 categories (auth, billing, bug, feature, logistics, incident), 8 templates each, plus multi-intent combinations (e.g., billing + bug).
3. **Label Layer**: Computes correct ground truth variables needed for grading. Adjusts priorities organically (e.g., High Churn boosts priority).
4. **Variation & Chaos Engine**: Introduces organic difficulty modifications:
   - Tones (angry, confused, polite, urgent)
   - Synonym substitutions (e.g., "password" → "passphrase")
   - Typo Injection (e.g., "loading" → "laoding")

The generator uses locked `random.seed()` values per task (42, 43, 44), ensuring identical episodes during repeated training or baseline inference.

---

### `server/app.py` — The Server

FastAPI application exposing both HTTP and WebSocket endpoints.

**HTTP Endpoints (backward-compatible):**
- `GET /` → Health check
- `POST /reset?task=<task_name>` → Resets environment for specified task
- `POST /step` (JSON body: `SupportOpsAction`) → Executes one action
- `GET /state` → Returns full internal state (for debugging)

**WebSocket Endpoint:**
- `WS /ws` → Persistent connection providing low latency. Each connection receives an **isolated** environment instance to allow multiple agents to train concurrently. It executes JSON messages seamlessly. 

---

### `server/support_ops_env_environment.py` — The Core RL Environment

This is the heart of the project. Implements the standard RL interface: `reset()` and `step()`.

**`reset(task)`** — Initializes an episode:
1. Calls the task configurator (`get_triage_sprint`, `get_queue_pressure`, or `get_incident_cascade`).
2. Generates complete ticket scenarios using the simulation engine.
3. Obscures hidden flags and truth labels.
4. Returns the initial `SupportOpsObservation`.

**`step(action)`** — Executes one action and returns `{observation, reward, done, info}`:

Process includes:
1. **Increment logic**: Global step count + churn risk progression (+0.02 per ticket).
2. **Action processing**:
   - `categorize`, `set_priority`, `route` (reward penalty `-0.02` for inaccuracy)
   - `resolve` (+0.02 shaping reward)
   - `merge_duplicate`, `submit`
   - Tools (`lookup_account`, `check_incident`) deduct budget and return data.
3. **Queue Health adjustments**: Slowly degrades. Resolving tickets recovers it.
4. **Termination check**: Halts heavily over-limit episodes or if step limits trigger penalities.
5. **Final grading on done**: See **Task-Specific Grading**. This adjusts the final step reward so that `sum(step_rewards) == grader_score`, strictly avoiding reward double-counting.

---

### `server/graders/grader.py` — Task-Specific Grading

Three grading functions, all normalized to `[0, 1]` truth evaluation:

**`grade_triage_sprint(state, ground_truth)`** — Easy:
- 35% category accuracy, 30% priority accuracy, 35% routing accuracy.

**`grade_queue_pressure(state, ground_truth)`** — Medium:
- 40% triage accuracy
- 20% duplicate detection
- 20% churn management
- 20% incident tracking

**`grade_incident_cascade(state, ground_truth)`** — Hard:
- 30% triage accuracy
- 25% tool usage
- 20% VIP handling
- 25% incident response (both tracking and triage resolution)

---

### `server/tasks/task_data.py` — Task Definitions

Fetches scenarios via `ticket_generator.py`:

**`get_triage_sprint()`** — Easy, 8 tickets:
- Pure triage, un-complex scenarios, zero tool budget, zero noise.
- `max_steps`: 40

**`get_queue_pressure()`** — Medium, 6 tickets:
- Introduces Duplicates, active Incidents, mixed moderate noise.
- `max_steps`: 30, `tool_budget`: 5

**`get_incident_cascade()`** — Hard, 5 tickets:
- Heavily relies on Incident correlations. Introduces high VIP/Fraud rates and high ambiguity.
- `max_steps`: 35, `tool_budget`: 5

---

### `agent/agent.py` — The Baseline Agent

A `SupportAgent` class that decides actions using a **rigid deterministic policy with organic LLM fallback**.

**Initialization:**
```python
SupportAgent(api_key, model="meta-llama/Meta-Llama-3-8B-Instruct", base_url=None)
```
Works via OpenAI-compatible API configurations. 

**Policy logic (`get_action`)**
- Prioritizes Duplicate management on Medium/Hard mode.
- Uses strict rule-based dictionary lookups and synonym lists (`CATEGORY_KEYWORDS`) to sort inputs and declare priority.
- Only consumes budget when encountering predefined tool-relevant phrases.

**LLM Fallback Pattern (`_llm_category`)**
The agent expects specific words like "crash", "payment", or "login". 
With the new `ticket_generator.py` variations, it will occasionally encounter terms that fully dodge these keyword lists ("glitch", "deducted", spelling errors).
* When a ticket fails the local heuristic search entirely, it triggers an LLM classification (`temperature=0.0`) asking the LLM to identify the ticket string.
* By design, the baseline LLM struggles here and makes classification errors, providing RL training room (~0.85 final average logic score).

---

### `inference.py` — Mandatory Baseline Script

Evaluates the environment standard:
1. Extrapolates variables from `.env` context
2. Establishes server connectivity via `EnvClient`
3. Generates 3 full sequences across easy/medium/hard profiles
4. Synthesizes `[START]`, `[STEP]`, `[END]` outputs format matching the Hackathon strict requirement

---

### `test_grader.py` — Validation Tests

Bypasses the agent entirely and executes "Perfect Path" iterations against Ground Truth states. Guarantees the math algorithms and grading systems perform precisely up to `1.000` standards on correctly processed environments.

---

## How to Run

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone and enter project
git clone <repo-url>
cd customer-support-openenv

# 3. Create .env with your HuggingFace token
echo "HF_TOKEN=hf_your_token_here" > .env

# 4. Install dependencies
uv sync

# 5. Terminal 1: Start server
uv run server

# 6. Terminal 2: Run inference baseline
uv run python inference.py

# 7. (Optional) Run grader environment validation
uv run python test_grader.py
```

---

## Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `HF_TOKEN` | Yes | — | HuggingFace API key for LLM calls |
| `API_BASE_URL` | No | `https://api.openai.com/v1` | LLM API endpoint |
| `MODEL_NAME` | No | `gpt-4o-mini` | Model identifier |
