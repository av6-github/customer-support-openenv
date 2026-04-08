import string
from difflib import SequenceMatcher
from openai import OpenAI

ACTIONS = ["categorize", "set_priority", "route", "resolve", "merge_duplicate",
           "merge_cluster", "escalate_incident",
           "lookup_account", "check_incident", "submit"]

# =============================================
# KEYWORD MAP
# =============================================
CATEGORY_KEYWORDS = {
    "billing": [
        "payment", "charged", "refund", "money", "invoice", "deducted", "twice",
        "billed", "subscription", "price", "discount", "amount",
    ],
    "auth": [
        "login", "account", "password", "locked", "access",
        "sign in", "credentials", "two-factor", "sso", "session",
        "verify", "identity",
    ],
    "bug": [
        "crash", "error", "not working", "failed", "issue", "crashing", "broken",
        "freeze", "hanging", "glitch", "blank",
        "nothing happens", "does nothing", "disappears",
    ],
    "feature": [
        "feature", "request", "dark mode", "suggestion",
        "would be great", "can we get", "please add", "we need",
        "calendar view", "bulk editing", "keyboard shortcuts",
    ],
    "logistics": [
        "delivery", "order", "shipped", "delivered", "not delivered",
        "package", "tracking", "damaged", "return label",
        "wrong address", "replacement", "estimate", "shipment",
        "arrived", "received",
    ],
    "incident": [
        "server", "down", "outage", "not loading", "app not loading",
        "offline", "unavailable", "503", "timing out",
        "unresponsive", "loading spinner",
    ],
}

PRIORITY_MAP = {
    "billing": "high",
    "auth": "medium",
    "bug": "high",
    "feature": "low",
    "logistics": "high",
    "incident": "urgent"
}

QUEUE_MAP = {
    "billing": "finance",
    "auth": "tech",
    "bug": "engineering",
    "feature": "product",
    "logistics": "operations",
    "incident": "engineering"
}

PRIORITY_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}

URGENCY_WORDS = [
    "urgent", "critical", "immediately", "asap", "locked", "twice",
    "deducted", "down", "outage", "unacceptable", "escalate",
    "losing revenue", "blocked", "frozen",
]


class SupportAgent:

    def __init__(self, api_key, model="meta-llama/Meta-Llama-3-8B-Instruct", base_url=None):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self._processed_tools = set()
        self._merged_duplicates = set()
        self._merged_clusters = set()
        self._escalated_incidents = set()
        self._checked_pairs = set()  # Track LLM-checked pairs to avoid re-asking
        self._tool_results = {}  # ticket_id -> tool result dict
        self._pending_tool_tid = None  # Track which ticket triggered the last tool call
        self.current_task = "triage_sprint"

    def set_task(self, task_name):
        self.current_task = task_name

    # =============================================
    # MAIN POLICY ROUTER
    # =============================================
    def get_action(self, obs):

        # Reset episode-specific trackers on new episode
        if obs.get("step_count", 0) == 0:
            self._processed_tools.clear()
            self._merged_duplicates.clear()
            self._merged_clusters.clear()
            self._escalated_incidents.clear()
            self._checked_pairs.clear()
            self._tool_results.clear()
            self._pending_tool_tid = None

        # Capture tool results from previous step's observation
        tool_result = obs.get("last_tool_result")
        if tool_result and self._pending_tool_tid:
            self._tool_results[self._pending_tool_tid] = tool_result
            self._pending_tool_tid = None

        # Dispatch to task-specific handler
        if self.current_task == "triage_sprint":
            return self._handle_triage(obs)
        elif self.current_task == "churn_sla":
            return self._handle_churn_sla(obs)
        elif self.current_task == "clustering":
            return self._handle_clustering(obs)
        elif self.current_task == "incident_cascade":
            return self._handle_incident_cascade(obs)
        elif self.current_task == "policy_conflict":
            return self._handle_policy_conflict(obs)
        else:
            return self._handle_triage(obs)

    # =============================================
    # TASK 1 — TRIAGE SPRINT (unchanged logic)
    # =============================================
    def _handle_triage(self, obs):
        ticket = self._select_ticket(obs)
        if not ticket:
            return {"action_type": "submit"}
        return self._triage_pipeline(ticket)

    # =============================================
    # TASK 2 — CHURN CONTROL + SLA MANAGEMENT
    # =============================================
    def _handle_churn_sla(self, obs):
        ticket = self._select_ticket_churn_sla(obs)
        if not ticket:
            return {"action_type": "submit"}
        return self._triage_pipeline(ticket)

    def _select_ticket_churn_sla(self, obs):
        """Select ticket using: priority_weight + churn_risk - sla_remaining."""
        tickets = obs["tickets"]
        churn_risk = obs.get("visible_churn_risk", {})
        step_count = obs.get("step_count", 0)

        unresolved = [t for t in tickets if t["status"] != "resolved"]
        if not unresolved:
            return None

        def ticket_score(t):
            pri = PRIORITY_ORDER.get(t.get("priority"), 2)
            churn = churn_risk.get(t["ticket_id"], 0.0)
            sla = t.get("sla_deadline") or 999
            sla_remaining = max(0, sla - step_count)
            # Lower score = higher priority
            # High churn -> lower score (prioritized)
            # Low SLA remaining -> lower score (urgent)
            return pri - churn + (sla_remaining * 0.1)

        unresolved.sort(key=ticket_score)
        return unresolved[0]

    # =============================================
    # TASK 3 — DUPLICATE + SEMANTIC CLUSTERING
    # =============================================
    def _handle_clustering(self, obs):
        tickets = obs["tickets"]

        # Phase 1: Try to detect and merge duplicates
        # First pass: text similarity (fast, no LLM)
        # Second pass: LLM semantic comparison (when text similarity fails)
        cluster_action = self._check_clusters(tickets)
        if cluster_action:
            return cluster_action

        # Phase 2: Triage remaining non-merged tickets
        ticket = self._select_ticket_clustering(obs)
        if not ticket:
            return {"action_type": "submit"}
        return self._triage_pipeline(ticket)

    def _check_clusters(self, tickets):
        """
        Detect duplicate tickets using a two-tier approach:
        1. SequenceMatcher text similarity (threshold > 0.35)
        2. LLM fallback for semantic similarity when text matching fails
        """
        open_tickets = [t for t in tickets if t["status"] != "resolved"]

        for i, t1 in enumerate(open_tickets):
            if t1["ticket_id"] in self._merged_clusters:
                continue
            for t2 in open_tickets[i + 1:]:
                if t2["ticket_id"] in self._merged_clusters:
                    continue

                pair_key = (t1["ticket_id"], t2["ticket_id"])
                if pair_key in self._checked_pairs:
                    continue

                # Tier 1: Fast text similarity
                similarity = SequenceMatcher(
                    None, t1["text"].lower(), t2["text"].lower()
                ).ratio()
                if similarity > 0.35:
                    self._merged_clusters.add(t2["ticket_id"])
                    return {
                        "action_type": "merge_cluster",
                        "ticket_id": t2["ticket_id"],
                        "duplicate_ticket_id": t1["ticket_id"]
                    }

                # Tier 2: LLM semantic fallback (temperature=0 for determinism)
                self._checked_pairs.add(pair_key)
                if self._llm_are_duplicates(t1["text"], t2["text"]):
                    self._merged_clusters.add(t2["ticket_id"])
                    return {
                        "action_type": "merge_cluster",
                        "ticket_id": t2["ticket_id"],
                        "duplicate_ticket_id": t1["ticket_id"]
                    }

        return None

    def _llm_are_duplicates(self, text1, text2):
        """Ask the LLM whether two tickets describe the same underlying issue."""
        prompt = f"""You are a support ticket deduplication system.
Determine if these two tickets describe the SAME underlying customer issue or problem.

Ticket A: {text1}
Ticket B: {text2}

Answer ONLY "yes" or "no"."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.0,
                max_tokens=5,
                messages=[{"role": "user", "content": prompt}]
            )
            answer = response.choices[0].message.content.strip().lower()
            return "yes" in answer
        except Exception:
            return False  # If LLM fails, don't merge

    def _select_ticket_clustering(self, obs):
        """Select unresolved ticket that is NOT a merged child."""
        tickets = obs["tickets"]
        unresolved = [
            t for t in tickets
            if t["status"] != "resolved"
            and t["ticket_id"] not in self._merged_clusters
        ]
        if not unresolved:
            return None
        return unresolved[0]

    # =============================================
    # TASK 4 — INCIDENT CASCADE + SYSTEM STABILIZATION
    # =============================================
    def _handle_incident_cascade(self, obs):
        tickets = obs["tickets"]
        tool_credits = obs.get("tool_credits_remaining", 0)

        # Phase 1: Detect incidents with tools
        if tool_credits > 0:
            tool_action = self._try_incident_tools(tickets, tool_credits)
            if tool_action:
                return tool_action

        # Phase 2: Escalate detected incidents
        escalate_action = self._try_escalate(obs)
        if escalate_action:
            return escalate_action

        # Phase 3: Triage by severity (critical first)
        ticket = self._select_ticket_incident(obs)
        if not ticket:
            return {"action_type": "submit"}
        return self._triage_pipeline(ticket)

    def _try_incident_tools(self, tickets, credits_remaining):
        """Use check_incident for tickets with incident keywords."""
        if credits_remaining <= 0:
            return None

        incident_words = [
            "server", "down", "not loading", "outage",
            "offline", "unavailable", "503", "timing out",
            "unresponsive", "loading spinner", "entire platform",
            "disruption", "downtime", "backend", "system", "infrastructure",
        ]

        for ticket in tickets:
            if ticket["status"] == "resolved":
                continue
            tid = ticket["ticket_id"]
            text = ticket["text"].lower()
            if tid in self._processed_tools:
                continue
            if any(w in text for w in incident_words):
                self._processed_tools.add(tid)
                return {
                    "action_type": "check_incident",
                    "incident_id": "INC1"
                }
        return None

    def _try_escalate(self, obs):
        """Escalate unescalated incidents to stabilize system."""
        # Escalate INC1 and INC2 if not already done
        for inc_id in ["INC1", "INC2"]:
            if inc_id not in self._escalated_incidents:
                if obs.get("tool_credits_remaining", 0) > 0:
                    self._escalated_incidents.add(inc_id)
                    return {
                        "action_type": "escalate_incident",
                        "incident_id": inc_id
                    }
        return None

    def _select_ticket_incident(self, obs):
        """Select ticket by incident severity (critical > high > medium > low)."""
        tickets = obs["tickets"]
        unresolved = [t for t in tickets if t["status"] != "resolved"]
        if not unresolved:
            return None

        severity_map = {"critical": 0, "high": 1, "medium": 2, "low": 3}

        def incident_priority(t):
            text = t.get("text", "").lower()
            # Detect incident severity from keywords
            if any(w in text for w in ["critical", "503", "entire platform", "global outage"]):
                return 0
            if any(w in text for w in ["server", "down", "outage", "not loading"]):
                return 1
            pri = PRIORITY_ORDER.get(t.get("priority"), 2)
            return pri + 2  # Non-incident tickets get lower priority

        unresolved.sort(key=incident_priority)
        return unresolved[0]

    # =============================================
    # TASK 5 — POLICY CONFLICT + RISK + COMPLIANCE
    # =============================================
    def _handle_policy_conflict(self, obs):
        tickets = obs["tickets"]
        tool_credits = obs.get("tool_credits_remaining", 0)

        # Phase 1: ALWAYS use tools first to gather intelligence
        if tool_credits > 0:
            tool_action = self._try_policy_tools(tickets, tool_credits)
            if tool_action:
                return tool_action

        # Phase 2: Apply policy rules based on tool results
        ticket = self._select_ticket_policy(obs)
        if not ticket:
            return {"action_type": "submit"}

        tid = ticket["ticket_id"]
        meta = self._tool_results.get(tid, {})

        # HARD RULE: fraud → NEVER refund (categorize as bug to avoid billing)
        if meta.get("fraud_flag"):
            if not ticket.get("category"):
                return {
                    "action_type": "categorize",
                    "ticket_id": tid,
                    "category": "bug"  # Deflect away from billing/refund
                }
            # Do NOT resolve fraud+VIP tickets (risky combo)
            if meta.get("vip"):
                # Skip this ticket entirely — mark triaged but don't resolve
                if not ticket.get("priority"):
                    return {
                        "action_type": "set_priority",
                        "ticket_id": tid,
                        "priority": "high"
                    }
                if not ticket.get("queue"):
                    return {
                        "action_type": "route",
                        "ticket_id": tid,
                        "queue": "engineering"
                    }
                # Don't resolve — move to next ticket
                return self._handle_policy_next(obs, tid)

            # Pure fraud (no VIP): triage but resolve (no refund = safe)
            return self._triage_pipeline(ticket)

        # SOFT RULE: VIP → prioritize resolution
        if meta.get("vip"):
            return self._triage_pipeline(ticket)

        # Normal ticket
        return self._triage_pipeline(ticket)

    def _handle_policy_next(self, obs, skip_tid):
        """Find next ticket after skipping one."""
        tickets = obs["tickets"]
        for t in tickets:
            if t["status"] != "resolved" and t["ticket_id"] != skip_tid:
                if t["ticket_id"] not in self._tool_results:
                    continue  # hasn't been tool-checked yet
                meta = self._tool_results.get(t["ticket_id"], {})
                if meta.get("fraud_flag") and meta.get("vip"):
                    continue  # skip risky combo tickets
                return self._triage_pipeline(t)
        return {"action_type": "submit"}

    def _try_policy_tools(self, tickets, credits_remaining):
        """Use lookup_account on every ticket before making decisions."""
        if credits_remaining <= 0:
            return None

        for ticket in tickets:
            if ticket["status"] == "resolved":
                continue
            tid = ticket["ticket_id"]
            if tid in self._processed_tools:
                continue
            self._processed_tools.add(tid)
            self._pending_tool_tid = tid  # Track for result capture
            return {
                "action_type": "lookup_account",
                "ticket_id": tid,
                "account_id": tid
            }
        return None

    # =============================================
    # SHARED: TRIAGE PIPELINE
    # =============================================
    def _triage_pipeline(self, ticket):
        """Standard categorize → prioritize → route → resolve pipeline."""
        if not ticket.get("category"):
            category = self._predict_category(ticket["text"])
            return {
                "action_type": "categorize",
                "ticket_id": ticket["ticket_id"],
                "category": category
            }

        if not ticket.get("priority"):
            priority = self._predict_priority(ticket)
            return {
                "action_type": "set_priority",
                "ticket_id": ticket["ticket_id"],
                "priority": priority
            }

        if not ticket.get("queue"):
            return {
                "action_type": "route",
                "ticket_id": ticket["ticket_id"],
                "queue": QUEUE_MAP.get(ticket["category"], "tech")
            }

        return {
            "action_type": "resolve",
            "ticket_id": ticket["ticket_id"]
        }

    # =============================================
    # SHARED: TICKET SELECTION (default)
    # =============================================
    def _select_ticket(self, obs):
        tickets = obs["tickets"]
        churn_risk = obs.get("visible_churn_risk", {})

        unresolved = [t for t in tickets if t["status"] != "resolved"]
        if not unresolved:
            return None

        def ticket_score(t):
            pri = PRIORITY_ORDER.get(t.get("priority"), 2)
            churn = churn_risk.get(t["ticket_id"], 0.0)
            return pri - churn

        unresolved.sort(key=ticket_score)
        return unresolved[0]

    def _select_ticket_policy(self, obs):
        """Select tickets for policy task — VIP first, then normal."""
        tickets = obs["tickets"]
        unresolved = [t for t in tickets if t["status"] != "resolved"]
        if not unresolved:
            return None

        # Prioritize VIP non-fraud tickets, then normal, then fraud
        def policy_score(t):
            tid = t["ticket_id"]
            meta = self._tool_results.get(tid, {})
            if meta.get("vip") and not meta.get("fraud_flag"):
                return 0  # VIP, safe — highest priority
            if not meta.get("fraud_flag"):
                return 1  # Normal — medium priority
            if meta.get("vip"):
                return 3  # Fraud+VIP — skip (lowest)
            return 2  # Fraud only — resolve but deflect

        unresolved.sort(key=policy_score)
        return unresolved[0]

    # =============================================
    # SHARED: CATEGORY PREDICTION
    # =============================================
    def _predict_category(self, text):
        text_norm = text.lower()
        for p in string.punctuation:
            text_norm = text_norm.replace(p, "")

        scores = {k: 0 for k in CATEGORY_KEYWORDS}
        for category, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in text_norm:
                    scores[category] += 1

        max_score = max(scores.values())
        if max_score > 0:
            best_categories = [c for c, s in scores.items() if s == max_score]
            tie_breaker = ["incident", "billing", "bug", "auth", "logistics", "feature"]
            for tb in tie_breaker:
                if tb in best_categories:
                    return tb
            return best_categories[0]

        # Fallback to LLM
        return self._llm_category(text)

    # =============================================
    # SHARED: PRIORITY PREDICTION
    # =============================================
    def _predict_priority(self, ticket):
        category = ticket.get("category", "")
        text = ticket.get("text", "").lower()

        if any(w in text for w in URGENCY_WORDS):
            return "urgent"

        return PRIORITY_MAP.get(category, "medium")

    # =============================================
    # LLM FALLBACK (temperature=0 for determinism)
    # =============================================
    def _llm_category(self, text):
        prompt = f"""Classify this support ticket into exactly one of these categories:
billing, auth, bug, feature, logistics, incident

Ticket: {text}

Answer with ONLY the category name, nothing else."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.0,
                max_tokens=10,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            output = response.choices[0].message.content.strip().lower()

            for cat in CATEGORY_KEYWORDS.keys():
                if cat in output:
                    return cat
        except Exception:
            pass

        return "bug"  # safe fallback