---
title: Customer Support OpenEnv
emoji: 🎧
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 8000
---

# Customer Support Ops: OpenEnv Challenge

## Overview & Motivation
A sophisticated reinforcement-learning environment simulating real-world SaaS customer support operations. Designed natively for the OpenEnv paradigm, this benchmark moves beyond "toy problems" (grid worlds) by accurately modeling the complexities of modern ticketing queues operations.

It evaluates autonomous agents across dynamic constraints including **SLA management, semantic duplicate clustering, cascading system incident tracking, and internal policy conflicts**. It forces models to deeply analyze their limited tool budget against compounding system-level risks, providing immediate value for real-world RL/agent deployment evaluations.

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
   - A highly constrained environment combining VIP users needing refunds against potential fraud actors. The agent must aggressively use the `lookup_account` tool to discover hidden metadata flags (VIP status vs Fraud_Flag) and make highly context-sensitive resolution choices. Refunding a fraudster yields fatal penalties.

---

## Novel Engineering & Architecture Mechanics

We ideated and built several extremely unique properties not natively present in base OpenEnv samples to enhance the complexity of modern LLM eval constraints:

1. **Progress-Based Dense Rewards over Compounding Penalties**: 
   Often, environments infinitely punish agents linearly per-step for missed SLAs or standing incidents causing instant episode deaths before exploration begins. We reversed this: our environment utilizes **One-Time SLA Timestamp Checking** and bounds decay by granting explicit immediate shape rewards (`+0.02` per critical ticket resolved, `+0.01` per tool check), ensuring long-horizon reward propagation.
2. **Organic Semantic Duplicate Generation**: 
   Rather than duplicate tickets identical string matches (which any hash map could solve), the internal generator operates a multi-pass pipeline to inherently paraphrase child tickets using realistic frustrated tones, explicitly forcing frontier models into genuine semantic comparison evaluations.
3. **The Tool-Budget tradeoff constraint**: 
   Providing the agent access to "god tools" (`lookup_account`) immediately solves complex tasks—except we bounded it natively via `tool_credits_remaining`. The agent must strategically determine if a ticket is sufficiently suspicious to warrant spending 1 of its 5 maximum credits.
4. **Exploit-Resistant Completion Gates**: 
   AI Agents often learn to "game" benchmarks by taking zero actions to avoid penalties (ending the episode for an un-penalized default score). All our graders multiply the final weight by a fractional `completion_gate` threshold—guaranteeing no artificial inflation occurs if genuine issues are ignored.

---

## Setup & Usage Instructions

Must run with Python 3.12+. We use `uv` for ultra-fast dependency management natively.

### 1. Repository Setup
```bash
git clone https://huggingface.co/spaces/av6sherlock/customer-support-openenv # Or your fork url
cd customer-support-openenv
```
Ensure you have `openenv-core` and the `openai` dependencies properly specified in `pyproject.toml`.

### 2. Configure Local Authentication (`.env`)
Create a `.env` file in the root. By default, the OpenEnv ecosystem operates using OpenAI compliance protocols. You must provide variables mimicking an OpenAI endpoint format (even if running local Hugging Face OpenRouter models!).

Example `.env` configuration mapping the official Hugging Face inference OpenAI compatibility route:
```env
HF_TOKEN=hf_your_huggingface_read_token_here
API_BASE_URL=https://router.huggingface.co/v1
MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
```

### 3. Run Inference Pipeline
The baseline inference script explicitly loads those variables out of `.env` directly using `openai.OpenAI()`.

First, you must start the environment server locally (leave this terminal open):
```bash
uv run server
```

Then, in a new terminal tab, run a single task (e.g. clustering):
```bash
TASK_NAME=clustering uv run python3 inference.py
```
Or run a full loop test mapping across all baseline behaviors without specifying `TASK_NAME`.

### 4. Deploy to Hugging Face
Once fully confident in your local grading compliance, push to OpenEnv. The backend grader will automatically inject premium evaluation credits dynamically.
```bash
uv run openenv push --repo-id <username>/<hugging-face-space-name>
```

---

## Baseline Scores
Testing against an optimized `Qwen/Qwen2.5-72B-Instruct` proxy yield the following normalized `[0.0 - 1.0]` performances natively simulating optimal routing logic post optimization phase:

- **Triage Sprint:** `0.963`
- **Churn SLA:** `0.852`
- **Clustering:** `0.694`
- **Incident Cascade:** `0.584`
- **Policy Conflict:** `0.470`

*Harder tasks genuinely stretch current LLM planning capabilities when bounded by limited action tokens and strict unyielding tool budgets.*
