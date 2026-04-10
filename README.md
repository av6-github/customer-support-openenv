---
title: Customer Support OpenEnv
emoji: 🎧
colorFrom: blue
colorTo: purple
sdk: docker
tags:
  - openenv
app_port: 8000
---

# Customer Support Ops: OpenEnv Challenge

## Overview & Motivation
A sophisticated reinforcement-learning environment simulating real-world SaaS customer support operations. Designed natively for the OpenEnv paradigm, this benchmark moves beyond "toy problems" (grid worlds) by accurately modeling the complexities of modern ticketing queues operations.

It evaluates autonomous agents across dynamic constraints including **SLA management, semantic duplicate clustering, cascading system incident tracking, and internal policy conflicts**. It forces models to deeply analyze their limited tool budget against compounding system-level risks, providing immediate value for real-world RL/agent deployment evaluations.

---

## 🏗️ System Architecture & Engineering 

Our environment operates on a decoupled client-server architecture, carefully engineered for thread-safety, determinism, and high-load parallel evaluation via testing graders:

1. **The Core Environment Server (`server/`)**: 
   - A FastAPI-driven backend serving HTTP and WebSocket endpoints (`app.py`).
   - Uses a robust **`SessionManager`** mapping isolated environment states strictly to `session_id`s, ensuring perfect thread-safety so multiple validation loops can interact concurrently without memory overlap.
   - Handles the raw logic of calculating step bounds, parsing actions into RL rewards, scaling penalties, and keeping real-time metrics of SLA bounds.
2. **Intelligent Probabilistic Tools (`server/tools/`)**:
   - `account_database.py` and `mock_tools.py` evaluate tool budget actions (`lookup_account`, `check_incident`). Instead of employing simplistic static flags, our mock tools use a unified hashing mechanism to deterministically but pseudo-randomly generate rich profiles (`fraud_score`, `vip_tier`, `lifetime_value`). This stops LLMs from cheating via strict pattern matching and enforces contextual reasoning.
3. **The Agent & Inference Runner (`agent/`, `inference.py`)**:
   - Includes a native baseline agent testing script. The standard HTTP `EnvClient` generates unique UUID sessions per inference run. 
4. **Structured Testing & Validation Metrics (`tests/`, `server/logger.py`)**:
   - Out-of-the-box support for strict bounds checking and validation parsing using `pytest`.
   - The standalone `MetricsLogger` intercepts simulation logic to autonomously dump perfect deterministic JSON traces capturing token count, step latency, tool executions, and step-rewards into `logs/metrics_{task}.json` for clean auditing.

---

## Action & Observation Spaces

### Observation Space
The environment emits a strict Pydantic-typed JSON interface matching the `SupportOpsObservation` contract:
- `tickets`: List of active dictionaries modeling customer issues (`ticket_id`, `text`, `status`, `churn_risk`, `sla_deadline`, `effort_cost`).
- `step_count`: Current step (int).
- `max_steps`: Total allowed steps before forced termination (int).
- `tool_credits_remaining`: The strict budget limiting how many lookups or queries the agent can perform.
- `queue_health`: A normalized float representing overall backlog size.
- `system_health`: Real-time tracking of platform stability (drastically impacted by active critical incidents).
- `last_tool_result`: Immediate dictionary response returning internal user or incident metadata when a tool is called.

### Action Space
Agents emit JSON actions mapping to 8 primary maneuvers:
- `action_type`: Evaluated string routing to [categorize, set_priority, route, resolve, merge_cluster, escalate_incident, lookup_account, check_incident].
- `ticket_id`: Target ID of the support issue string.
- `category` / `priority` / `queue`: Metadata adjustment strings.
- `duplicate_ticket_id`: Target ticket ID for linking in cluster merge actions.
- `account_id` / `incident_id`: UUID parameters targeting tool lookups.

---

## Tasks & Expected Difficulty

We implemented 5 distinctly graded tasks progressing linearly in required complexity and reasoning capabilities.

1. **Triage Sprint (`triage_sprint`) - Easy**
   - Purely focuses on NLP classification. Graded on categorizing, prioritizing, and properly routing a high volume of straightforward requests.
2. **Churn SLA (`churn_sla`) - Medium**
   - Introduces explicit deadlines (`sla_deadline`) and scaling `churn_risk`. High-risk customers must be prioritized over simple requests. Graded on timestamp-based resolution efficiency.
3. **Semantic Clustering (`clustering`) - Medium/Hard**
   - The environment dynamically generates paraphrased duplicate tickets. The agent must semantically group overlapping issues and enforce **transitive parent-child linkage** (`merge_cluster`) to alleviate backlog congestion instead of resolving identical tickets redundantly.
4. **Incident Cascade (`incident_cascade`) - Hard**
   - Simulates a SaaS platform outage. The agent must correlate tickets to underlying incidents while `system_health` continuously decays. Requires judicious use of tool budgeting (`check_incident`) and strategic `escalate_incident` actions to prevent system death.
5. **Policy Conflict (`policy_conflict`) - Hard**
   - A highly constrained environment combining VIP users needing refunds against potential fraud actors. The agent must aggressively use the probabilistically generated `lookup_account` tool to discover hidden metadata flags and make highly context-sensitive resolution choices. Refunding a fraudster yields fatal penalties.

---

## 🛠️ Setup & Execution Instructions

Must run with Python 3.12+. We natively use `uv` for ultra-fast dependency management.

### 1. Repository Setup
```bash
git clone https://huggingface.co/spaces/av6sherlock/customer-support-openenv # Or your fork url
cd customer-support-openenv
```
Ensure you have the required dependencies mapped in `pyproject.toml` or `requirements.txt` (including `httpx` and `pytest` for running integrations).

### 2. Configure Local Authentication (`.env`)
Create a `.env` file in the root. By default, the OpenEnv ecosystem operates using OpenAI compliance protocols. You must provide variables mimicking an OpenAI endpoint format.

Example `.env` configuration:
```env
HF_TOKEN=your_huggingface_read_token_here
API_BASE_URL=https://router.huggingface.co/v1
MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
```

### 3. Run Inference Pipeline
First, you must start the environment server locally (leave this terminal open):
```bash
uv run server
```

Then, in a new terminal tab, run a single task (e.g., policy conflict):
```bash
TASK_NAME=policy_conflict uv run python3 inference.py
```
*Note: Inference will automatically generate clean debugging tracks in `logs/metrics_{task_name}.json` without polluting the standard evaluation output expected by graders.*
Or run a full loop test mapping across all baseline behaviors natively by not injecting `TASK_NAME`.

### 4. Running Validation & Tests
To verify the thread-safety bounds and state integration logic of the simulated environments:
```bash
PYTHONPATH=. uv run pytest tests/
```
Or execute the automated OpenEnv submission baseline protocol:
```bash
python3 test_grader.py
```

### 5. Deploy to Hugging Face
Once fully confident in your local grading compliance, push to OpenEnv. The backend grader will automatically evaluate your task grades utilizing internal test runners using parallel session isolation.
```bash
uv run openenv push --repo-id <username>/<hugging-face-space-name>
```

---

## Baseline Scores
Testing against an optimized `Qwen/Qwen2.5-72B-Instruct` proxy yield the following normalized `[0.0 - 1.0]` performances over fully constrained environments:

- **Triage Sprint:** `0.963`
- **Churn SLA:** `0.852`
- **Clustering:** `0.694`
- **Incident Cascade:** `0.849`  *(Updated constraints)*
- **Policy Conflict:** `0.870`  *(Updated constraints)*

*Harder tasks genuinely stretch current LLM planning capabilities when bounded by limited action tokens and strict probabilistic tool profiles.*
