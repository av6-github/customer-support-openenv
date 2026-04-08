---
title: Customer Support OpenEnv
emoji: 🎧
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 8000
---

# Support Ops Environment

## Motivation
A reinforcement-learning environment simulating real-world SaaS support operations. Designed to model the complexities of modern ticketing queues, evaluating agents on task prioritization, churn management, duplicate detection, and tool usage across varied scenarios.

## Action & Observation Spaces
### Observation Space
- `tickets`: List of currently active tickets.
- `step_count`: Current step.
- `max_steps`: Episode length limit.
- `tool_credits_remaining`: Allowed budget for tool use.
- `queue_health`: Metric measuring the global state of the support queue.
- `visible_churn_risk`: Risk metrics for high priority customers.

### Action Space
- `action_type`: One of [categorize, set_priority, route, resolve, merge_duplicate, lookup_account, check_incident, submit].
- `ticket_id`: Target ticket ID.
- `category`: Ticket category (str).
- `priority`: Priority level (str).
- `queue`: Routing destination (str).
- `duplicate_ticket_id`: Parent ticket ID for duplicates.
- `account_id`: Account ID for tools.
- `incident_id`: Incident ID for tools.

## Tasks
1. **Triage Sprint (easy)**: Focuses purely on correct categorization, prioritization, and routing.
2. **Queue Under Pressure (medium)**: Introduces duplicates, churn metrics, and incident tracking, requiring strategic queue management.
3. **Incident Cascade (hard)**: Introduces VIP customers and requires judicious use of tools with a limited budget to correctly resolve issues.

## Setup & Execution
Must run with Python 3.9+. We use `uv` for ultra-fast dependency and environment management.

1. **Install `uv` (if not already installed):**
   - **macOS / Linux:**
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```
   - **Windows (PowerShell):**
     ```powershell
     powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
     ```
     After installation, **close and reopen your terminal** for PATH changes to take effect.

     If `uv` is still not recognized, add it to PATH manually:
     1. Open **Start → Settings → System → About → Advanced system settings → Environment Variables**
     2. Under "User variables", select **Path** → **Edit** → **New**
     3. Add: `%USERPROFILE%\.cargo\bin`
     4. Click **OK** on all dialogs, then open a **new** terminal

     Alternatively, you can install via **pip** (works everywhere):
     ```bash
     pip install uv
     ```

2. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd customer-support-openenv
   ```

3. **Configure Environment variables:**
   Create a `.env` file in the root directory and add your Hugging Face API token:
   ```env
   HF_TOKEN=your_huggingface_token_here
   ```

4. **Install Dependencies:**
   ```bash
   uv sync
   ```

5. **Start the Environment Server:**
   Open a terminal and run the server (leave this running):
   ```bash
   uv run server
   ```

## Inference & Baselines
In a **new terminal tab**, run the baseline inference script using the HuggingFace endpoint via OpenAI compatibility:
```bash
uv run python inference.py
```
*Expected Baseline Scores (GPT-4o-mini)*:
- Triage Sprint: ~0.85
- Queue Pressure: ~0.70
- Incident Cascade: ~0.60
