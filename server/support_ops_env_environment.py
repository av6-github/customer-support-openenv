from models import SupportOpsObservation, SupportOpsState, Ticket
from server.tasks.task_data import (
    get_triage_sprint,
    get_queue_pressure,
    get_incident_cascade
)
from server.tools import mock_tools
from server.graders import grader


class SupportOpsEnvironment:

    def __init__(self):
        self._state = None
        self._task_name = None
        self._ground_truth = {}
        self._cumulative_shaping = 0.0

    # -----------------------------
    # RESET
    # -----------------------------
    def reset(self, task: str = "triage_sprint"):
        self._task_name = task
        self._cumulative_shaping = 0.0

        if task == "triage_sprint":
            data = get_triage_sprint()
        elif task == "queue_pressure":
            data = get_queue_pressure()
        else:
            data = get_incident_cascade()

        tickets = {
            t["ticket_id"]: Ticket(
                ticket_id=t["ticket_id"],
                text=t["text"]
            )
            for t in data["tickets"]
        }

        # store ground truth
        self._ground_truth = {
            t["ticket_id"]: t for t in data["tickets"]
        }

        self._state = SupportOpsState(
            tickets=tickets,
            max_steps=data.get("max_steps", 20),
            tool_credits_remaining=data.get("tool_budget", 5)
        )

        return self._build_observation()

    # -----------------------------
    # STEP
    # -----------------------------
    def step(self, action: dict):

        reward = 0.0
        done = False

        action_type = action.get("action_type")
        ticket_id = action.get("ticket_id")

        # increment step
        self._state.step_count += 1

        # -----------------------------
        # CHURN INCREASE
        # -----------------------------
        for tid in self._state.tickets:
            current = self._state.churn_risk.get(tid, 0.1)
            self._state.churn_risk[tid] = min(1.0, current + 0.02)

        # -----------------------------
        # ACTION HANDLERS
        # (No positive step rewards — grader is authoritative)
        # (Only small shaping penalties for wrong answers)
        # -----------------------------

        if action_type == "categorize":
            category = action.get("category")
            self._state.tickets[ticket_id].category = category
            self._state.categorized[ticket_id] = category

            if category != self._ground_truth[ticket_id]["category"]:
                reward -= 0.02

        elif action_type == "set_priority":
            priority = action.get("priority")
            self._state.tickets[ticket_id].priority = priority
            self._state.prioritized[ticket_id] = priority

            if priority != self._ground_truth[ticket_id]["priority"]:
                reward -= 0.02

        elif action_type == "route":
            queue = action.get("queue")
            self._state.tickets[ticket_id].queue = queue
            self._state.routed[ticket_id] = queue

            if queue != self._ground_truth[ticket_id]["queue"]:
                reward -= 0.02

            # Incident tracking
            if "incident_id" in self._ground_truth[ticket_id]:
                inc = self._ground_truth[ticket_id]["incident_id"]
                if inc not in self._state.active_incidents:
                    self._state.active_incidents.append(inc)

        # Duplicate merge
        elif action_type == "merge_duplicate":
            child = action.get("ticket_id")
            parent = action.get("duplicate_ticket_id")
            if child and parent:
                self._state.duplicates[child] = parent

        # -----------------------------
        # TOOL CALLS
        # -----------------------------
        elif action_type == "lookup_account":
            if self._state.tool_credits_remaining > 0:
                self._state.tool_credits_remaining -= 1
                result = mock_tools.lookup_account(action.get("account_id"))
                # store tool result so agent can use it
                self._state.last_tool_result = result
            else:
                reward -= 0.05

        elif action_type == "check_incident":
            if self._state.tool_credits_remaining > 0:
                self._state.tool_credits_remaining -= 1
                result = mock_tools.check_incident(action.get("incident_id"))
                self._state.last_tool_result = result
            else:
                reward -= 0.05

        # -----------------------------
        # RESOLUTION
        # -----------------------------
        elif action_type == "resolve":
            self._state.tickets[ticket_id].status = "resolved"
            if ticket_id not in self._state.resolved_tickets:
                self._state.resolved_tickets.append(ticket_id)
            # small shaping reward for completing a ticket
            reward += 0.02

        elif action_type == "submit":
            done = True

        # -----------------------------
        # CHURN PENALTY (small shaping)
        # -----------------------------
        for tid, risk in self._state.churn_risk.items():
            if risk > 0.7 and tid not in self._state.resolved_tickets:
                reward -= 0.01

        # -----------------------------
        # QUEUE HEALTH UPDATE
        # -----------------------------
        resolved_count = len(self._state.resolved_tickets)
        self._state.queue_health -= 0.02
        self._state.queue_health += resolved_count * 0.005
        self._state.queue_health = max(0.0, min(1.0, self._state.queue_health))

        # -----------------------------
        # TERMINATION
        # -----------------------------
        if self._state.queue_health < 0.4:
            done = True
            reward -= 0.1

        if self._state.step_count >= self._state.max_steps:
            done = True

        # Track cumulative shaping (before final grading)
        self._cumulative_shaping += reward

        # -----------------------------
        # FINAL GRADING (authoritative score on done)
        # Emit: grader_score - all_prior_shaping so that
        # sum of all step rewards == grader_score
        # -----------------------------
        if done:
            grader_score = 0.0
            if self._task_name == "triage_sprint":
                grader_score = grader.grade_triage_sprint(
                    self._state.__dict__,
                    self._ground_truth
                )
            elif self._task_name == "queue_pressure":
                grader_score = grader.grade_queue_pressure(
                    self._state.__dict__,
                    self._ground_truth
                )
            elif self._task_name == "incident_cascade":
                grader_score = grader.grade_incident_cascade(
                    self._state.__dict__,
                    self._ground_truth
                )

            # Final reward = grader_score - prior accumulated shaping
            # so total_reward across all steps = grader_score
            reward = grader_score - (self._cumulative_shaping - reward)

        return {
            "observation": self._build_observation(),
            "reward": reward,
            "done": done,
            "info": {}
        }

    # -----------------------------
    # OBSERVATION BUILDER
    # -----------------------------
    def _build_observation(self):

        return SupportOpsObservation(
            tickets=list(self._state.tickets.values()),
            step_count=self._state.step_count,
            max_steps=self._state.max_steps,
            tool_credits_remaining=self._state.tool_credits_remaining,
            queue_health=self._state.queue_health,
            visible_churn_risk=self._state.churn_risk
        ).dict()

    # -----------------------------
    # STATE EXPORT
    # -----------------------------
    def state(self):
        if self._state:
            return self._state.dict()
        return {}

# -----------------------------
# STATE (FULL INTERNAL STATE)
# -----------------------------
def state(self):
    """
    Returns full internal environment state.
    Useful for debugging / evaluation.
    """

    return self._state.dict()