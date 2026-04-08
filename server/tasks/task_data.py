from ticket_generator import generate_task_data


def get_triage_sprint():
    """Task 1: Clean tickets, low ambiguity, no duplicates."""
    return generate_task_data("triage_sprint")


def get_churn_sla():
    """Task 2: Churn control + SLA management."""
    return generate_task_data("churn_sla")


def get_clustering():
    """Task 3: Duplicate + semantic clustering."""
    return generate_task_data("clustering")


def get_incident_cascade():
    """Task 4: Incident cascade + system stabilization."""
    return generate_task_data("incident_cascade")


def get_policy_conflict():
    """Task 5: Policy conflict + risk + compliance."""
    return generate_task_data("policy_conflict")