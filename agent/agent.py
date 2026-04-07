import os
import string
from difflib import SequenceMatcher
from openai import OpenAI

ACTIONS = ["categorize", "set_priority", "route", "resolve", "merge_duplicate",
           "lookup_account", "check_incident", "submit"]

CATEGORY_KEYWORDS = {
    "billing": ["payment", "charged", "refund", "money", "invoice", "deducted", "twice"],
    "auth": ["login", "account", "password", "locked", "access"],
    "bug": ["crash", "error", "not working", "failed", "issue", "crashing", "broken"],
    "feature": ["feature", "request", "dark mode", "suggestion"],
    "logistics": ["delivery", "order", "shipped", "delivered", "not delivered"],
    "incident": ["server", "down", "outage", "not loading", "app not loading"]
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

# Priority ordering for ticket selection
PRIORITY_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}


class SupportAgent:

    def __init__(self, api_key, model="meta-llama/Meta-Llama-3-8B-Instruct", base_url=None):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self._processed_tools = set()  # track which tickets we've used tools on
        self._merged_duplicates = set()
        self.current_task = "triage_sprint"

    def set_task(self, task_name):
        self.current_task = task_name

    # -----------------------------
    # MAIN POLICY
    # -----------------------------
    def get_action(self, obs):

        # Reset episode-specific trackers if this is a new episode
        if obs.get("step_count", 0) == 0:
            self._processed_tools.clear()
            self._merged_duplicates.clear()

        tickets = obs["tickets"]
        tool_credits = obs.get("tool_credits_remaining", 0)

        # ---------------------------
        # HARD PHASE 1: Tools Early
        # ---------------------------
        if self.current_task == "incident_cascade":
            if tool_credits > 0:
                tool_action = self._try_tool_usage(tickets, tool_credits)
                if tool_action:
                    return tool_action

        # ---------------------------
        # MEDIUM & HARD PHASE: Duplicates First
        # (Easy task ignores duplicates completely)
        # ---------------------------
        if self.current_task in ["queue_pressure", "incident_cascade"]:
            dupe_action = self._check_duplicates(tickets)
            if dupe_action:
                return dupe_action

        # ---------------------------
        # MEDIUM: Minimal Tools
        # ---------------------------
        if self.current_task == "queue_pressure":
            if tool_credits > 0:
                tool_action = self._try_tool_usage(tickets, tool_credits)
                if tool_action:
                    return tool_action

        # ---------------------------
        # ALL TASKS: Triage Phase
        # ---------------------------
        ticket = self._select_ticket(obs)

        if not ticket:
            return {"action_type": "submit"}

        # Step 1: Categorize if not done
        if not ticket.get("category"):
            category = self._predict_category(ticket["text"])
            return {
                "action_type": "categorize",
                "ticket_id": ticket["ticket_id"],
                "category": category
            }

        # Step 2: Set priority
        if not ticket.get("priority"):
            priority = self._predict_priority(ticket)
            return {
                "action_type": "set_priority",
                "ticket_id": ticket["ticket_id"],
                "priority": priority
            }

        # Step 3: Route
        if not ticket.get("queue"):
            return {
                "action_type": "route",
                "ticket_id": ticket["ticket_id"],
                "queue": QUEUE_MAP.get(ticket["category"], "tech")
            }

        # Step 4: Resolve
        return {
            "action_type": "resolve",
            "ticket_id": ticket["ticket_id"]
        }

    # -----------------------------
    # TICKET SELECTION (urgency + churn aware)
    # -----------------------------
    def _select_ticket(self, obs):

        tickets = obs["tickets"]
        churn_risk = obs.get("visible_churn_risk", {})

        unresolved = [t for t in tickets if t["status"] != "resolved"]

        if not unresolved:
            return None

        def ticket_score(t):
            # Lower score = higher priority
            pri = PRIORITY_ORDER.get(t.get("priority"), 2)
            churn = churn_risk.get(t["ticket_id"], 0.0)
            # Subtract churn to prioritize high-churn tickets
            return pri - churn

        unresolved.sort(key=ticket_score)
        return unresolved[0]

    # -----------------------------
    # PRIORITY PREDICTION (smarter)
    # -----------------------------
    def _predict_priority(self, ticket):
        category = ticket.get("category", "")
        text = ticket.get("text", "").lower()

        # Urgency signals in text
        urgent_words = ["urgent", "locked", "twice", "deducted", "down", "outage"]
        if any(w in text for w in urgent_words):
            return "urgent"

        return PRIORITY_MAP.get(category, "medium")

    # -----------------------------
    # DUPLICATE DETECTION
    # -----------------------------
    def _check_duplicates(self, tickets):
        """Find and merge duplicate tickets based on text similarity."""
        open_tickets = [t for t in tickets if t["status"] != "resolved"]

        for i, t1 in enumerate(open_tickets):
            if t1["ticket_id"] in self._merged_duplicates:
                continue
            for t2 in open_tickets[i + 1:]:
                if t2["ticket_id"] in self._merged_duplicates:
                    continue
                similarity = SequenceMatcher(
                    None, t1["text"].lower(), t2["text"].lower()
                ).ratio()
                if similarity > 0.5:
                    self._merged_duplicates.add(t2["ticket_id"])
                    # merge the later ticket into the earlier one
                    return {
                        "action_type": "merge_duplicate",
                        "ticket_id": t2["ticket_id"],
                        "duplicate_ticket_id": t1["ticket_id"]
                    }
        return None

    # -----------------------------
    # TOOL USAGE DECISIONS
    # -----------------------------
    def _try_tool_usage(self, tickets, credits_remaining):
        """Decide whether to use tools based on ticket signals."""
        if credits_remaining <= 0:
            return None

        for ticket in tickets:
            if ticket["status"] == "resolved":
                continue
            tid = ticket["ticket_id"]
            text = ticket["text"].lower()

            if tid in self._processed_tools:
                continue

            # Use check_incident for incident-related tickets
            if any(w in text for w in ["server", "down", "not loading", "outage"]):
                self._processed_tools.add(tid)
                return {
                    "action_type": "check_incident",
                    "incident_id": "INC1"
                }

            # Use lookup_account for billing/fraud signals
            if any(w in text for w in ["refund", "charged", "twice", "payment failed"]):
                self._processed_tools.add(tid)
                return {
                    "action_type": "lookup_account",
                    "account_id": tid
                }

        return None

    # -----------------------------
    # CATEGORY PREDICTION (Robust Text Normalization + Scoring)
    # -----------------------------
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
            
            # Tie breaking rule
            tie_breaker = ["incident", "billing", "bug", "auth", "logistics", "feature"]
            for tb in tie_breaker:
                if tb in best_categories:
                    return tb
            
            return best_categories[0]

        # fallback to LLM
        return self._llm_category(text)

    # -----------------------------
    # LLM FALLBACK
    # -----------------------------
    def _llm_category(self, text):
        prompt = f"""
Classify this support ticket into one of:
billing, auth, bug, feature, logistics, incident

Ticket: {text}

Answer ONLY the category.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.0,
                max_tokens=10,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            output = response.choices[0].message.content.lower()

            for cat in CATEGORY_KEYWORDS.keys():
                if cat in output:
                    return cat
        except Exception as e:
            pass

        return "bug"  # safe fallback