from models import SupportOpsObservation, SupportOpsState, Ticket
from server.tasks.task_data import (
    get_triage_sprint,
    get_churn_sla,
    get_clustering,
    get_incident_cascade,
    get_policy_conflict,
)
from server.tools import mock_tools
from server.graders import grader


TASK_DISPATCH = {
    "triage_sprint": get_triage_sprint,
    "churn_sla": get_churn_sla,
    "clustering": get_clustering,
    "incident_cascade": get_incident_cascade,
    "policy_conflict": get_policy_conflict,
}


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

        loader = TASK_DISPATCH.get(task)
        if not loader:
            raise ValueError(f"Unknown task: {task}")
        data = loader()

        tickets = {
            t["ticket_id"]: Ticket(
                ticket_id=t["ticket_id"],
                text=t["text"],
                churn_risk=t.get("churn_risk", 0.0),
                sla_deadline=t.get("sla_deadline"),
                effort_cost=t.get("effort_cost", 1),
            )
            for t in data["tickets"]
        }

        # store ground truth (includes hidden labels)
        self._ground_truth = {
            t["ticket_id"]: t for t in data["tickets"]
        }

        self._state = SupportOpsState(
            tickets=tickets,
            max_steps=data.get("max_steps", 20),
            tool_credits_remaining=data.get("tool_budget", 5),
        )

        # Initialize churn risk from ticket data
        for tid, t in self._ground_truth.items():
            if t.get("churn_risk", 0) > 0:
                self._state.churn_risk[tid] = t["churn_risk"]

        # Initialize incident metadata
        for tid, t in self._ground_truth.items():
            if t.get("incident_id"):
                self._state.incident_mapping[tid] = t["incident_id"]
            if t.get("incident_severity"):
                self._state.incident_severity[tid] = t["incident_severity"]

        # Initialize policy metadata
        for tid, t in self._ground_truth.items():
            meta = {}
            for key in ("vip", "fraud_flag", "account_age", "lifetime_value", "account_id"):
                if key in t:
                    meta[key] = t[key]
            if meta:
                self._state.ticket_metadata[tid] = meta

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
        # CHURN INCREASE (all tasks)
        # -----------------------------
        for tid in self._state.tickets:
            current = self._state.churn_risk.get(tid, 0.1)
            self._state.churn_risk[tid] = min(1.0, current + 0.02)

        # -----------------------------
        # SLA TRACKING (churn_sla task)
        # -----------------------------
        if self._task_name == "churn_sla":
            for tid, ticket in self._state.tickets.items():
                if ticket.sla_deadline is not None and tid not in self._state.resolved_tickets:
                    if self._state.step_count > ticket.sla_deadline and tid not in self._state.penalized_sla:
                        reward -= 0.10  # SLA violation penalty per ticket (applied once)
                        self._state.penalized_sla.add(tid)

        # -----------------------------
        # SYSTEM HEALTH DECAY (incident_cascade task)
        # -----------------------------
        if self._task_name == "incident_cascade":
            self._state.system_health -= 0.01  # Base decay
            
            # Reward for resolving incidents instead of punishing for unresolved ones
            critical_resolved = sum(1 for tid, inc_id in self._state.incident_mapping.items()
                                    if tid in self._state.resolved_tickets and 
                                    self._state.incident_severity.get(tid) == "critical")
            
            self._state.system_health = min(1.0, self._state.system_health + (critical_resolved * 0.02))
            self._state.system_health = max(0.0, self._state.system_health)

        # =============================
        # ACTION HANDLERS
        # =============================

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

        # --- Duplicate merge (legacy) ---
        elif action_type == "merge_duplicate":
            child = action.get("ticket_id")
            parent = action.get("duplicate_ticket_id")
            if child and parent:
                self._state.duplicates[child] = parent

        # --- Cluster merge (Task 3) ---
        elif action_type == "merge_cluster":
            child = action.get("ticket_id")
            parent = action.get("duplicate_ticket_id")
            if child and parent:
                gt_child = self._ground_truth.get(child, {})
                gt_parent = self._ground_truth.get(parent, {})
                child_cluster = gt_child.get("cluster_id")
                parent_cluster = gt_parent.get("cluster_id")

                if child_cluster and parent_cluster and child_cluster == parent_cluster:
                    # Correct merge with transitive closure
                    self._state.clusters[child] = parent if parent not in self._state.clusters else self._state.clusters[parent]
                else:
                    # Incorrect merge → penalty
                    reward -= 0.03

        # --- Escalate incident (Task 4) ---
        elif action_type == "escalate_incident":
            inc_id = action.get("incident_id")
            if inc_id and self._state.tool_credits_remaining > 0:
                self._state.tool_credits_remaining -= 1
                # Mark incident as escalated → boost system health
                if inc_id not in self._state.active_incidents:
                    self._state.active_incidents.append(inc_id)
                self._state.system_health = min(1.0, self._state.system_health + 0.05)
            elif self._state.tool_credits_remaining <= 0:
                reward -= 0.05

        # -----------------------------
        # TOOL CALLS
        # -----------------------------
        elif action_type == "lookup_account":
            if self._state.tool_credits_remaining > 0:
                self._state.tool_credits_remaining -= 1
                acc_id = action.get("account_id", "")

                # For policy_conflict task, return rich metadata
                if self._task_name == "policy_conflict" and ticket_id:
                    meta = self._state.ticket_metadata.get(ticket_id, {})
                    result = {
                        "vip": meta.get("vip", False),
                        "fraud_flag": meta.get("fraud_flag", False),
                        "account_age": meta.get("account_age", 1),
                        "lifetime_value": meta.get("lifetime_value", 0.0),
                    }
                else:
                    result = mock_tools.lookup_account(acc_id)

                self._state.last_tool_result = result
                reward += 0.01  # Small immediate reward for using tool wisely
            else:
                reward -= 0.05

        elif action_type == "check_incident":
            if self._state.tool_credits_remaining > 0:
                self._state.tool_credits_remaining -= 1
                result = mock_tools.check_incident(action.get("incident_id"))
                self._state.last_tool_result = result
                reward += 0.01  # Small immediate reward for using tool wisely
            else:
                reward -= 0.05

        # -----------------------------
        # RESOLUTION
        # -----------------------------
        elif action_type == "resolve":
            self._state.tickets[ticket_id].status = "resolved"
            if ticket_id not in self._state.resolved_tickets:
                self._state.resolved_tickets.append(ticket_id)
                self._state.resolution_step[ticket_id] = self._state.step_count

                # Effort cost: advance step clock by (effort_cost - 1) extra ticks
                if self._task_name == "churn_sla":
                    effort = self._state.tickets[ticket_id].effort_cost
                    if effort > 1:
                        self._state.step_count += (effort - 1)

                # Incident resolution boosts system health
                if self._task_name == "incident_cascade" and ticket_id in self._state.incident_mapping:
                    self._state.system_health = min(1.0, self._state.system_health + 0.08)

            # small shaping reward for completing a ticket
            reward += 0.02

            # Policy conflict: penalize resolving fraud tickets with refund-like categories
            if self._task_name == "policy_conflict":
                meta = self._state.ticket_metadata.get(ticket_id, {})
                if meta.get("fraud_flag") and self._state.categorized.get(ticket_id) == "billing":
                    reward -= 0.1  # Heavy penalty: refunding a fraudster

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
        resolved_this_step = 1 if action_type == "resolve" else 0
        self._state.queue_health -= 0.02
        self._state.queue_health += resolved_this_step * 0.01  # Reward per-step resolutions
        self._state.queue_health = max(0.0, min(1.0, self._state.queue_health))

        # -----------------------------
        # TERMINATION
        # -----------------------------
        if self._state.queue_health < 0.4:
            done = True
            reward -= 0.1

        if self._task_name == "incident_cascade" and self._state.system_health <= 0.0:
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
                    self._state.__dict__, self._ground_truth
                )
            elif self._task_name == "churn_sla":
                grader_score = grader.grade_churn_sla(
                    self._state.__dict__, self._ground_truth
                )
            elif self._task_name == "clustering":
                grader_score = grader.grade_clustering(
                    self._state.__dict__, self._ground_truth
                )
            elif self._task_name == "incident_cascade":
                grader_score = grader.grade_incident_cascade(
                    self._state.__dict__, self._ground_truth
                )
            elif self._task_name == "policy_conflict":
                grader_score = grader.grade_policy_conflict(
                    self._state.__dict__, self._ground_truth
                )

            # Final reward = grader_score - prior accumulated shaping
            # so total_reward across all steps = grader_score
            reward_diff = grader_score - (self._cumulative_shaping - reward)
            
            # User constraint: individual step rewards must be strictly bound.
            # Compensatory rewards that push a single step > 1.0 are invalid.
            reward = reward_diff
        
        # Enforce strict OpenEnv [-1.0, 1.0] bound on all step rewards
        reward = max(-1.0, min(1.0, float(reward)))

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
            system_health=self._state.system_health,
            visible_churn_risk=self._state.churn_risk,
            last_tool_result=self._state.last_tool_result
        ).dict()

    # -----------------------------
    # STATE EXPORT
    # -----------------------------
    def state(self):
        if self._state:
            return self._state.dict()
        return {}
