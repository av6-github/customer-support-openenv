import random

SEED_MAP = {
    "triage_sprint": 42,
    "queue_pressure": 43,
    "incident_cascade": 44
}

ISSUE_TEMPLATES = {
    "billing": [
        "Payment failed but money deducted",
        "Charged twice for same order",
        "Refund not processed"
    ],
    "auth": [
        "Unable to login",
        "Account locked",
        "Password reset not working"
    ],
    "bug": [
        "App crashing on startup",
        "Feature not loading",
        "Unexpected error shown"
    ],
    "feature": [
        "Feature request for dark mode",
        "Suggestion for new dashboard",
        "Add ability to export to CSV"
    ],
    "logistics": [
        "Order not delivered",
        "Shipped to wrong address",
        "Package arrived damaged"
    ],
    "incident": [
        "Server down",
        "App not loading",
        "Global outage reported"
    ]
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

def generate_tickets(task_name, n=8):
    random.seed(SEED_MAP[task_name])

    tickets = []

    categories = list(ISSUE_TEMPLATES.keys())

    for i in range(n):
        category = random.choice(categories)
        text = random.choice(ISSUE_TEMPLATES[category])

        ticket = {
            "ticket_id": f"T{i+1}",
            "text": text,
            "category": category,
            "priority": PRIORITY_MAP[category],
            "queue": QUEUE_MAP[category]
        }

        tickets.append(ticket)

    return tickets