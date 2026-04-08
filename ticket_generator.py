"""
4-Layer Ticket Generator — Simulation Engine
=============================================
Layer 1: Scenario Generation (incidents, duplicates, flags)
Layer 2: Text Generation (templates, tones, noise)
Layer 3: Label Generation (category, priority, queue, hidden attrs)
Layer 4: Variation & Chaos Engine (synonyms, restructuring, ambiguity)
"""

import random
import string


# =============================================
# SEED MAP (deterministic per task)
# =============================================
SEED_MAP = {
    "triage_sprint": 42,
    "churn_sla": 43,
    "clustering": 44,
    "incident_cascade": 45,
    "policy_conflict": 46,
}


# =============================================
# LAYER 2 — TEXT TEMPLATES
# =============================================

# Base intent templates per category
INTENT_TEMPLATES = {
    "billing": [
        "I was charged twice for my subscription",
        "Payment failed but the amount was still deducted",
        "Refund has not been processed after 10 days",
        "My card was billed an incorrect amount",
        "There is a duplicate charge on my account",
        "I see an unauthorized transaction on my statement",
        "The promotional discount was not applied to my invoice",
        "My subscription was renewed at the wrong price",
    ],
    "auth": [
        "I can't log into my account",
        "My password reset link is not working",
        "Account has been locked after multiple attempts",
        "Two-factor authentication code never arrives",
        "SSO integration is failing for my organization",
        "I am unable to verify my identity on the portal",
        "Session keeps expiring every few minutes",
        "My credentials are no longer accepted after the migration",
    ],
    "bug": [
        "App crashes immediately on startup",
        "Clicking the submit button does nothing",
        "Data disappears after switching between tabs",
        "The export function generates a blank file",
        "Search results show completely irrelevant items",
        "The notification badge shows the wrong count",
        "Page layout breaks on mobile devices",
        "Dropdown menu options are duplicated",
    ],
    "feature": [
        "Can we get a dark mode option",
        "It would be great to have multi-language support",
        "Please add the ability to export data to CSV",
        "A calendar view for tasks would be really helpful",
        "We need bulk editing capabilities for admin users",
        "Can you add keyboard shortcuts for common actions",
        "An audit log feature would improve our compliance",
        "We need webhook integration for third-party tools",
    ],
    "logistics": [
        "My order has not been delivered yet",
        "Package was shipped to the wrong address",
        "The item arrived damaged and unusable",
        "Tracking link has shown no updates for a week",
        "I received someone else's items instead of mine",
        "The delivery estimate keeps changing every day",
        "Return label is not generating properly",
        "My replacement shipment has no tracking information",
    ],
    "incident": [
        "Your servers seem to be down",
        "The entire app is not loading at all",
        "Global outage reported across all regions",
        "Everything is timing out for our whole team",
        "The platform has been completely unresponsive since this morning",
        "API endpoints are returning 503 errors",
        "Dashboard is stuck on a loading spinner for everyone",
        "None of our integrations can connect to your service",
    ],
}

# Paraphrase map: for each base template, a list of realistic rephrasings
# describing THE SAME issue in different words (like a second customer reporting it)
PARAPHRASE_MAP = {
    # billing
    "I was charged twice for my subscription": [
        "There's a double charge on my account for the same subscription",
        "My billing shows two identical subscription charges this month",
        "I noticed a duplicate subscription fee on my latest statement",
    ],
    "Payment failed but the amount was still deducted": [
        "My payment didn't go through but the money was taken anyway",
        "Transaction shows failed but my bank account was still charged",
        "The payment was declined yet the amount disappeared from my balance",
    ],
    "Refund has not been processed after 10 days": [
        "I'm still waiting on a refund that was promised over a week ago",
        "It's been 10+ days and my refund still hasn't shown up",
        "The refund I was told I'd receive still hasn't hit my account",
    ],
    "My card was billed an incorrect amount": [
        "The charge on my card doesn't match what I was supposed to pay",
        "I was billed the wrong amount on my credit card",
        "The amount deducted from my card is different from my order total",
    ],
    "There is a duplicate charge on my account": [
        "My account shows the same charge appearing twice",
        "I can see a repeated charge that shouldn't be there",
    ],
    "I see an unauthorized transaction on my statement": [
        "There's a charge on my statement I didn't make",
        "An unknown transaction appeared on my billing history",
    ],
    "The promotional discount was not applied to my invoice": [
        "My promo code didn't reduce the price on the invoice",
        "The discount I was supposed to get is missing from my bill",
    ],
    "My subscription was renewed at the wrong price": [
        "The renewal charge is higher than what I was paying before",
        "I was charged a different price when my plan auto-renewed",
    ],
    # auth
    "I can't log into my account": [
        "I'm unable to access my account no matter what I try",
        "My login isn't working — I keep getting an error",
        "I've been locked out and can't get into my account",
    ],
    "My password reset link is not working": [
        "The reset password link I received says it's expired or invalid",
        "I clicked the password reset email but it just shows an error",
    ],
    "Account has been locked after multiple attempts": [
        "My account got locked because I entered the wrong password too many times",
        "I'm locked out after several failed login attempts",
    ],
    "Two-factor authentication code never arrives": [
        "I never get the 2FA code when trying to log in",
        "The verification code for two-step login isn't being sent",
    ],
    "SSO integration is failing for my organization": [
        "Our company's single sign-on stopped working with your platform",
        "SSO login for our org keeps failing with an auth error",
    ],
    "I am unable to verify my identity on the portal": [
        "The identity verification step keeps rejecting my documents",
        "I can't complete the ID verification process on your site",
    ],
    "Session keeps expiring every few minutes": [
        "I keep getting logged out every couple of minutes",
        "My session times out way too quickly while I'm still using it",
    ],
    "My credentials are no longer accepted after the migration": [
        "Since the system migration my old login doesn't work anymore",
        "After the platform update my username and password stopped working",
    ],
    # bug
    "App crashes immediately on startup": [
        "The application crashes right after I open it",
        "Every time I launch the app it immediately closes",
        "I can't even get past the loading screen before it crashes",
    ],
    "Clicking the submit button does nothing": [
        "The submit button is completely unresponsive when I click it",
        "Nothing happens when I press submit on the form",
    ],
    "Data disappears after switching between tabs": [
        "When I switch tabs all my entered data is gone",
        "My work vanishes every time I navigate to another tab and back",
    ],
    "The export function generates a blank file": [
        "When I export my data the file is completely empty",
        "The downloaded export file has no content in it",
    ],
    "Search results show completely irrelevant items": [
        "The search feature returns results that have nothing to do with my query",
        "When I search for something the results are totally unrelated",
    ],
    "The notification badge shows the wrong count": [
        "My notification counter is displaying an incorrect number",
        "The unread notification count doesn't match my actual notifications",
    ],
    "Page layout breaks on mobile devices": [
        "The page looks completely broken when I open it on my phone",
        "The UI is messed up and unusable on mobile browsers",
    ],
    "Dropdown menu options are duplicated": [
        "The dropdown shows each option listed twice",
        "There are duplicate entries appearing in the dropdown menus",
    ],
    # feature
    "Can we get a dark mode option": [
        "It would be nice to have a dark theme available",
    ],
    "It would be great to have multi-language support": [
        "Please consider adding support for multiple languages",
    ],
    "Please add the ability to export data to CSV": [
        "We really need a CSV export feature for our data",
    ],
    "A calendar view for tasks would be really helpful": [
        "Having tasks displayed in a calendar format would be useful",
    ],
    "We need bulk editing capabilities for admin users": [
        "Admins should be able to edit multiple items at once",
    ],
    "Can you add keyboard shortcuts for common actions": [
        "Keyboard shortcuts would speed up our workflow significantly",
    ],
    "An audit log feature would improve our compliance": [
        "We need an activity log for compliance and auditing purposes",
    ],
    "We need webhook integration for third-party tools": [
        "Please add webhook support so we can connect external services",
    ],
    # logistics
    "My order has not been delivered yet": [
        "I'm still waiting for my order and it hasn't arrived",
        "My package never showed up even though it was supposed to be here",
    ],
    "Package was shipped to the wrong address": [
        "You sent my package to a different address than what I entered",
        "My delivery went to the wrong location",
    ],
    "The item arrived damaged and unusable": [
        "What I received was broken and I can't use it",
        "My order arrived in damaged condition",
    ],
    "Tracking link has shown no updates for a week": [
        "The tracking page hasn't changed in over a week",
        "My package tracking has been stuck with no movement for days",
    ],
    "I received someone else's items instead of mine": [
        "The package I got contained items that aren't mine",
        "You sent me the wrong person's order",
    ],
    "The delivery estimate keeps changing every day": [
        "My estimated delivery date changes daily and I never know when it'll arrive",
        "The expected delivery keeps getting pushed back every single day",
    ],
    "Return label is not generating properly": [
        "I can't generate a return shipping label from your site",
        "The return label page gives an error when I try to create one",
    ],
    "My replacement shipment has no tracking information": [
        "The replacement you sent has no tracking number attached",
        "I can't track my replacement order because there's no tracking info",
    ],
    # incident
    "Your servers seem to be down": [
        "It looks like your servers are offline right now",
        "Is your service down? Nothing is loading for me",
    ],
    "The entire app is not loading at all": [
        "The app won't load anything — just a blank screen",
        "Nothing loads when I open the application",
    ],
    "Global outage reported across all regions": [
        "We're seeing a worldwide outage affecting all our offices",
        "Users in every region are reporting the service is completely down",
    ],
    "Everything is timing out for our whole team": [
        "All requests are timing out for everyone on our team",
        "Our entire team is experiencing timeout errors on every action",
    ],
    "The platform has been completely unresponsive since this morning": [
        "Since this morning the platform hasn't responded to anything",
        "The system has been dead since early today with no signs of recovery",
    ],
    "API endpoints are returning 503 errors": [
        "All our API calls are failing with 503 service unavailable",
        "We keep getting 503 errors from every endpoint we hit",
    ],
    "Dashboard is stuck on a loading spinner for everyone": [
        "The dashboard just shows a spinner and never loads for any of us",
        "Everyone on our team sees an infinite loading screen on the dashboard",
    ],
    "None of our integrations can connect to your service": [
        "All our connected integrations lost connection to your platform",
        "Every third-party integration we use shows your service as unreachable",
    ],
}

# Tone modifiers applied to templates
TONE_MODIFIERS = {
    "neutral": [
        "{text}",
        "Hi, {text}",
        "Hello, {text}",
    ],
    "angry": [
        "{text}!! This is unacceptable!",
        "WHY is this happening?! {text}",
        "{text}. I am extremely frustrated.",
        "THIS IS RIDICULOUS. {text}",
    ],
    "confused": [
        "I'm not sure what happened but {text}",
        "This is strange — {text}",
        "Not sure if this is just me but {text}",
        "Um, {text}? I don't understand.",
    ],
    "polite": [
        "Hi, I hope you're well. {text}. Thank you!",
        "Could you please help? {text}",
        "I'd appreciate assistance with this: {text}",
        "Sorry to bother, but {text}",
    ],
    "urgent": [
        "URGENT: {text}",
        "{text} — this needs immediate attention!",
        "CRITICAL: {text}. We are losing revenue.",
        "Please escalate immediately. {text}",
    ],
}

# Synonym substitutions for variation
SYNONYMS = {
    "charged": ["billed", "debited"],
    "payment": ["transaction", "charge"],
    "refund": ["reimbursement", "credit back"],
    "login": ["sign in", "access my account", "authenticate"],
    "password": ["credentials", "passphrase"],
    "locked": ["frozen", "blocked", "disabled"],
    "crash": ["freeze", "hang", "stop responding"],
    "error": ["issue", "problem", "glitch"],
    "not working": ["malfunctioning", "broken", "acting up"],
    "order": ["purchase", "shipment"],
    "delivered": ["arrived", "received", "showed up"],
    "shipped": ["dispatched", "sent out"],
    "server": ["system", "infrastructure", "backend"],
    "down": ["offline", "unavailable", "not reachable"],
    "outage": ["disruption", "downtime"],
    "feature": ["functionality", "capability"],
    "request": ["suggestion", "proposal"],
}

# Typo injection patterns
TYPO_MAP = {
    "payment": ["payemnt", "paymnet", "paymet"],
    "account": ["acount", "accoutn", "acconut"],
    "password": ["pasword", "passwrod", "passowrd"],
    "loading": ["loadign", "laoding", "loadin"],
    "delivered": ["deliverd", "delievered", "delivred"],
    "received": ["recieved", "recevied", "recived"],
    "subscription": ["subscripton", "subscrption", "subscribtion"],
    "working": ["workign", "wrking", "workin"],
}

# Multi-intent combinations (category1 + category2)
MULTI_INTENT_COMBOS = [
    ("billing", "auth", "I got charged twice and now I can't even log in to dispute it"),
    ("billing", "bug", "The payment page keeps glitching and I was charged the wrong amount"),
    ("auth", "bug", "After resetting my password the app started crashing"),
    ("logistics", "billing", "The order arrived damaged and I still haven't gotten my refund"),
    ("bug", "feature", "The search is completely broken — also, can we get a filter option?"),
    ("incident", "auth", "The entire site is down and nobody on our team can sign in"),
    ("incident", "billing", "Systems are down and our automatic payments just failed"),
    ("logistics", "bug", "Tracking page shows an error and my shipment status is stuck"),
]


# =============================================
# LABEL MAPS
# =============================================

PRIORITY_MAP = {
    "billing": "high",
    "auth": "medium",
    "bug": "high",
    "feature": "low",
    "logistics": "high",
    "incident": "urgent",
}

QUEUE_MAP = {
    "billing": "finance",
    "auth": "tech",
    "bug": "engineering",
    "feature": "product",
    "logistics": "operations",
    "incident": "engineering",
}

PRIORITY_ESCALATION_WORDS = [
    "urgent", "critical", "immediately", "asap", "losing revenue",
    "unacceptable", "escalate", "blocked", "frozen",
]


# =============================================
# LAYER 1 — SCENARIO GENERATION
# =============================================

def _generate_scenario(rng, n_tickets, difficulty):
    """
    Generate structured scenario metadata for each ticket.
    Returns list of TicketMeta dicts.
    """
    categories = list(INTENT_TEMPLATES.keys())
    metas = []

    # --- Decide global events ---

    # Incident cluster
    has_incident = False
    incident_id = None
    if difficulty in ("medium", "hard"):
        has_incident = rng.random() < (0.4 if difficulty == "hard" else 0.35)
    if has_incident:
        incident_id = f"INC{rng.randint(100, 999)}"

    # --- Generate per-ticket metadata ---
    for i in range(n_tickets):
        cat = rng.choice(categories)
        meta = {
            "index": i,
            "base_category": cat,
            "incident_id": None,
            "duplicate_of": None,
            "fraud_flag": False,
            "vip": False,
            "churn_risk": round(rng.uniform(0.05, 0.3), 2),
        }

        # Incident assignment
        if has_incident and cat == "incident":
            meta["incident_id"] = incident_id
        elif has_incident and rng.random() < 0.3:
            # Some non-incident tickets also affected by the incident
            meta["base_category"] = "incident"
            meta["incident_id"] = incident_id

        # Special flags
        if difficulty in ("medium", "hard"):
            if rng.random() < 0.15:
                meta["fraud_flag"] = True
            if rng.random() < 0.15:
                meta["vip"] = True
            if rng.random() < 0.25:
                meta["churn_risk"] = round(rng.uniform(0.6, 0.95), 2)

        if difficulty == "hard":
            if rng.random() < 0.2:
                meta["vip"] = True
            if rng.random() < 0.2:
                meta["fraud_flag"] = True

        metas.append(meta)

    # --- Duplicate clusters ---
    if difficulty in ("medium", "hard") and n_tickets >= 4:
        n_dupe_clusters = rng.randint(1, min(3, n_tickets // 3))
        available = list(range(n_tickets))
        rng.shuffle(available)

        for _ in range(n_dupe_clusters):
            if len(available) < 2:
                break
            parent_idx = available.pop(0)
            child_idx = available.pop(0)
            # Child copies parent's category
            metas[child_idx]["base_category"] = metas[parent_idx]["base_category"]
            metas[child_idx]["duplicate_of"] = f"T{parent_idx + 1}"
            if metas[parent_idx]["incident_id"]:
                metas[child_idx]["incident_id"] = metas[parent_idx]["incident_id"]

    # --- Force some incidents for hard task ---
    if difficulty == "hard" and not has_incident:
        incident_id = f"INC{rng.randint(100, 999)}"
        # Pick first ticket without special role
        for m in metas:
            if m["base_category"] != "incident" and not m["duplicate_of"]:
                m["base_category"] = "incident"
                m["incident_id"] = incident_id
                break
        # Add a second incident ticket
        for m in metas:
            if m["base_category"] != "incident" and not m["duplicate_of"]:
                m["base_category"] = "incident"
                m["incident_id"] = f"INC{rng.randint(100, 999)}"
                break

    return metas


# =============================================
# LAYER 4 — VARIATION & CHAOS ENGINE
# =============================================

def _apply_synonyms(rng, text, probability=0.3):
    """Randomly swap words with synonyms."""
    words = text.split()
    result = []
    for word in words:
        clean = word.lower().strip(string.punctuation)
        if clean in SYNONYMS and rng.random() < probability:
            replacement = rng.choice(SYNONYMS[clean])
            # Preserve original casing of first char
            if word[0].isupper():
                replacement = replacement.capitalize()
            # Preserve trailing punctuation
            trailing = ""
            for c in reversed(word):
                if c in string.punctuation:
                    trailing = c + trailing
                else:
                    break
            result.append(replacement + trailing)
        else:
            result.append(word)
    return " ".join(result)


def _inject_typos(rng, text, probability=0.08):
    """Randomly introduce typos in known words."""
    words = text.split()
    result = []
    for word in words:
        clean = word.lower().strip(string.punctuation)
        if clean in TYPO_MAP and rng.random() < probability:
            typo = rng.choice(TYPO_MAP[clean])
            # Preserve casing
            if word[0].isupper():
                typo = typo.capitalize()
            trailing = ""
            for c in reversed(word):
                if c in string.punctuation:
                    trailing = c + trailing
                else:
                    break
            result.append(typo + trailing)
        else:
            result.append(word)
    return " ".join(result)


def _apply_tone(rng, text, difficulty):
    """Apply a tone modifier to the text."""
    if difficulty == "easy":
        tones = ["neutral", "polite"]
    elif difficulty == "medium":
        tones = ["neutral", "angry", "confused", "polite"]
    else:
        tones = ["neutral", "angry", "confused", "polite", "urgent"]

    tone = rng.choice(tones)
    template = rng.choice(TONE_MODIFIERS[tone])
    return template.format(text=text)


# =============================================
# LAYER 2+3+4 COMBINED — TICKET GENERATION
# =============================================

def _generate_ticket(rng, meta, index, difficulty, parent_text=None):
    """
    From scenario metadata → final ticket with text + labels.
    If parent_text is provided (for duplicates), generate a paraphrase instead.
    """
    cat = meta["base_category"]

    # --- Layer 2: Pick base text ---
    if parent_text and meta.get("duplicate_of"):
        # DUPLICATE: paraphrase the parent's base issue
        paraphrases = PARAPHRASE_MAP.get(parent_text)
        if paraphrases:
            text = rng.choice(paraphrases)
        else:
            # Fallback: use synonym substitution on parent text
            text = _apply_synonyms(rng, parent_text, probability=0.6)
    else:
        # Normal ticket: pick from templates
        use_multi = (
            difficulty in ("medium", "hard")
            and rng.random() < 0.15
            and not meta["duplicate_of"]
        )

        if use_multi:
            combo = rng.choice(MULTI_INTENT_COMBOS)
            if combo[0] == cat or combo[1] == cat:
                text = combo[2]
            else:
                matching = [c for c in MULTI_INTENT_COMBOS if c[0] == cat]
                if matching:
                    combo = rng.choice(matching)
                    text = combo[2]
                else:
                    text = rng.choice(INTENT_TEMPLATES[cat])
        else:
            text = rng.choice(INTENT_TEMPLATES[cat])

    # Store the raw base text BEFORE applying variations (for paraphrase lookup)
    meta["_base_text"] = text

    # --- Layer 4: Apply variations ---
    syn_prob = {"easy": 0.1, "medium": 0.25, "hard": 0.4}[difficulty]
    text = _apply_synonyms(rng, text, probability=syn_prob)

    # Tone
    text = _apply_tone(rng, text, difficulty)

    # Typo injection (only on medium/hard)
    if difficulty != "easy":
        typo_prob = {"medium": 0.06, "hard": 0.10}[difficulty]
        text = _inject_typos(rng, text, probability=typo_prob)

    # --- Layer 3: Labels ---
    priority = PRIORITY_MAP[cat]

    if meta["churn_risk"] > 0.7:
        if priority == "medium":
            priority = "high"
        elif priority == "low":
            priority = "medium"

    text_lower = text.lower()
    if any(w in text_lower for w in PRIORITY_ESCALATION_WORDS):
        if priority in ("medium", "low"):
            priority = "high"

    queue = QUEUE_MAP[cat]

    ticket = {
        "ticket_id": f"T{index + 1}",
        "text": text,
        "category": cat,
        "priority": priority,
        "queue": queue,
    }

    # Hidden attributes
    if meta["incident_id"]:
        ticket["incident_id"] = meta["incident_id"]
    if meta["duplicate_of"]:
        ticket["duplicate_of"] = meta["duplicate_of"]
    if meta["fraud_flag"]:
        ticket["fraud_flag"] = True
    if meta["vip"]:
        ticket["vip"] = True
    if meta["churn_risk"] > 0.5:
        ticket["churn_risk"] = meta["churn_risk"]

    return ticket


# =============================================
# PUBLIC API
# =============================================

DIFFICULTY_MAP = {
    "triage_sprint": "easy",
    "churn_sla": "medium",
    "clustering": "medium",
    "incident_cascade": "hard",
    "policy_conflict": "hard",
}

TICKET_COUNT = {
    "triage_sprint": 8,
    "churn_sla": 6,
    "clustering": 8,
    "incident_cascade": 5,
    "policy_conflict": 5,
}

MAX_STEPS = {
    "triage_sprint": 40,
    "churn_sla": 35,
    "clustering": 40,
    "incident_cascade": 35,
    "policy_conflict": 30,
}

TOOL_BUDGET = {
    "triage_sprint": 0,
    "churn_sla": 0,
    "clustering": 0,
    "incident_cascade": 5,
    "policy_conflict": 5,
}


def generate_tickets(task_name, n=None):
    """
    Generate deterministic, realistic support tickets for a given task.

    Args:
        task_name: One of the 5 registered tasks
        n: Override number of tickets (optional)

    Returns:
        list of ticket dicts with ground truth labels + hidden attributes
    """
    seed = SEED_MAP[task_name]
    rng = random.Random(seed)

    difficulty = DIFFICULTY_MAP[task_name]
    n_tickets = n or TICKET_COUNT[task_name]

    # Layer 1: Scenario
    metas = _generate_scenario(rng, n_tickets, difficulty)

    # Layer 2+3+4: Generate tickets
    # Two-pass: generate parents first, then duplicates with parent text
    tickets = [None] * n_tickets

    # Pass 1: Generate non-duplicate tickets
    for i, meta in enumerate(metas):
        if not meta.get("duplicate_of"):
            ticket = _generate_ticket(rng, meta, i, difficulty)
            tickets[i] = ticket

    # Pass 2: Generate duplicates using parent's base text for paraphrasing
    for i, meta in enumerate(metas):
        if meta.get("duplicate_of"):
            parent_tid = meta["duplicate_of"]  # e.g. "T1"
            parent_idx = int(parent_tid[1:]) - 1
            parent_base_text = metas[parent_idx].get("_base_text", "")
            ticket = _generate_ticket(rng, meta, i, difficulty, parent_text=parent_base_text)
            tickets[i] = ticket

    # ---- Task-specific post-processing ----

    if task_name == "churn_sla":
        # Assign SLA deadlines, effort costs, and churn risk profiles
        sla_deadlines = [3, 5, 2, 6, 4, 3]
        effort_costs  = [2, 1, 3, 1, 2, 1]
        churn_values  = [0.85, 0.3, 0.9, 0.2, 0.75, 0.6]
        for i, t in enumerate(tickets):
            t["sla_deadline"] = sla_deadlines[i % len(sla_deadlines)]
            t["effort_cost"]  = effort_costs[i % len(effort_costs)]
            t["churn_risk"]   = churn_values[i % len(churn_values)]

    elif task_name == "clustering":
        # Derive cluster IDs organically from the generator's duplicate_of chains
        # The scenario generator already creates duplicate pairs naturally
        cluster_counter = 0
        parent_to_cluster = {}  # parent_ticket_id -> cluster_id

        for t in tickets:
            dupe_of = t.get("duplicate_of")
            if dupe_of:
                if dupe_of not in parent_to_cluster:
                    cluster_counter += 1
                    parent_to_cluster[dupe_of] = f"C{cluster_counter}"
                    # Assign cluster_id to the parent ticket too
                    for p in tickets:
                        if p["ticket_id"] == dupe_of:
                            p["cluster_id"] = parent_to_cluster[dupe_of]
                            break
                t["cluster_id"] = parent_to_cluster[dupe_of]

    elif task_name == "incident_cascade":
        # Assign incident IDs and severity levels
        incident_configs = [
            {"incident_id": "INC1", "incident_severity": "critical"},
            {"incident_id": "INC1", "incident_severity": "critical"},
            {"incident_id": "INC2", "incident_severity": "high"},
            {"incident_id": None,   "incident_severity": None},
            {"incident_id": "INC2", "incident_severity": "high"},
        ]
        for i, t in enumerate(tickets):
            cfg = incident_configs[i % len(incident_configs)]
            if cfg["incident_id"]:
                t["incident_id"] = cfg["incident_id"]
                t["incident_severity"] = cfg["incident_severity"]
                t["category"] = "incident"
                t["priority"] = "urgent" if cfg["incident_severity"] == "critical" else "high"
                t["queue"]    = "engineering"

    elif task_name == "policy_conflict":
        # Assign risk/compliance metadata
        policy_configs = [
            {"vip": True,  "fraud_flag": False, "account_age": 5,  "lifetime_value": 12000.0, "account_id": "VIP001"},
            {"vip": False, "fraud_flag": True,  "account_age": 1,  "lifetime_value": 200.0,   "account_id": "FRD002F"},
            {"vip": True,  "fraud_flag": True,  "account_age": 3,  "lifetime_value": 8500.0,  "account_id": "VIP003F"},
            {"vip": False, "fraud_flag": False, "account_age": 7,  "lifetime_value": 4500.0,  "account_id": "REG004"},
            {"vip": True,  "fraud_flag": False, "account_age": 10, "lifetime_value": 25000.0, "account_id": "VIP005"},
        ]
        for i, t in enumerate(tickets):
            cfg = policy_configs[i % len(policy_configs)]
            t["vip"]            = cfg["vip"]
            t["fraud_flag"]     = cfg["fraud_flag"]
            t["account_age"]    = cfg["account_age"]
            t["lifetime_value"] = cfg["lifetime_value"]
            t["account_id"]     = cfg["account_id"]

    return tickets


def generate_task_data(task_name):
    """
    Generate full task configuration including tickets, max_steps, and tool_budget.

    Returns:
        dict with 'tickets', 'max_steps', 'tool_budget'
    """
    tickets = generate_tickets(task_name)
    return {
        "tickets": tickets,
        "max_steps": MAX_STEPS[task_name],
        "tool_budget": TOOL_BUDGET.get(task_name, 0),
    }