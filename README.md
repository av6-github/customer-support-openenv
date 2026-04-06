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
Must run with Python 3.9+ and have `uv` installed.
```bash
uv sync
uv run server
```

## Inference & Baselines
Run the baseline inference script using standard OpenAI models:
```bash
export OPENAI_API_KEY=your_key_here
uv run python inference.py
```
*Expected Baseline Scores (GPT-4o-mini)*:
- Triage Sprint: ~0.85
- Queue Pressure: ~0.70
- Incident Cascade: ~0.60
