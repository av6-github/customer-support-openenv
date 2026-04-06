def grade_triage_sprint(state, ground_truth):
    """
    Easy task grader — pure triage accuracy.
    Normalized to [0, 1] via dimension-weighted scoring.
    """
    total = len(ground_truth)
    if total == 0:
        return 0.0

    cat_correct = 0
    pri_correct = 0
    rte_correct = 0

    for tid, gt in ground_truth.items():
        if state["categorized"].get(tid) == gt["category"]:
            cat_correct += 1
        if state["prioritized"].get(tid) == gt["priority"]:
            pri_correct += 1
        if state["routed"].get(tid) == gt["queue"]:
            rte_correct += 1

    cat_score = cat_correct / total
    pri_score = pri_correct / total
    rte_score = rte_correct / total

    return 0.35 * cat_score + 0.30 * pri_score + 0.35 * rte_score


def grade_queue_pressure(state, ground_truth):
    """
    Medium task grader — triage + churn + duplicates + incidents.
    Normalized to [0, 1].

    Weights:
      - Triage accuracy   40%
      - Duplicate merges   20%
      - Churn management   20%
      - Incident tracking  20%
    """
    total = len(ground_truth)
    if total == 0:
        return 0.0

    # --- Triage accuracy (40%) ---
    cat_correct = 0
    pri_correct = 0
    rte_correct = 0
    for tid, gt in ground_truth.items():
        if state["categorized"].get(tid) == gt["category"]:
            cat_correct += 1
        if state["prioritized"].get(tid) == gt["priority"]:
            pri_correct += 1
        if state["routed"].get(tid) == gt["queue"]:
            rte_correct += 1

    triage_score = (cat_correct + pri_correct + rte_correct) / (total * 3)

    # --- Duplicate detection (20%) ---
    expected_dupes = {
        tid: gt["duplicate_of"]
        for tid, gt in ground_truth.items()
        if "duplicate_of" in gt
    }
    if expected_dupes:
        dupe_correct = sum(
            1 for child, parent in expected_dupes.items()
            if state.get("duplicates", {}).get(child) == parent
        )
        dupe_score = dupe_correct / len(expected_dupes)
    else:
        dupe_score = 1.0  # no dupes expected → full marks

    # --- Churn management (20%) ---
    # High-churn tickets should be resolved
    churn_tickets = [
        tid for tid, gt in ground_truth.items()
        if gt.get("churn_risk", 0) > 0.5
    ]
    if churn_tickets:
        resolved = state.get("resolved_tickets", [])
        churn_resolved = sum(1 for tid in churn_tickets if tid in resolved)
        churn_score = churn_resolved / len(churn_tickets)
    else:
        churn_score = 1.0

    # --- Incident tracking (20%) ---
    expected_incidents = set(
        gt["incident_id"]
        for gt in ground_truth.values()
        if "incident_id" in gt
    )
    if expected_incidents:
        tracked = set(state.get("active_incidents", []))
        inc_found = len(expected_incidents & tracked)
        incident_score = inc_found / len(expected_incidents)
    else:
        incident_score = 1.0

    return (
        0.40 * triage_score
        + 0.20 * dupe_score
        + 0.20 * churn_score
        + 0.20 * incident_score
    )


def grade_incident_cascade(state, ground_truth):
    """
    Hard task grader — triage + tool usage + VIP + incidents.
    Normalized to [0, 1].

    Weights:
      - Triage accuracy    30%
      - Tool usage         25%
      - VIP handling       20%
      - Incident response  25%
    """
    total = len(ground_truth)
    if total == 0:
        return 0.0

    # --- Triage accuracy (30%) ---
    cat_correct = 0
    pri_correct = 0
    rte_correct = 0
    for tid, gt in ground_truth.items():
        if state["categorized"].get(tid) == gt["category"]:
            cat_correct += 1
        if state["prioritized"].get(tid) == gt["priority"]:
            pri_correct += 1
        if state["routed"].get(tid) == gt["queue"]:
            rte_correct += 1

    triage_score = (cat_correct + pri_correct + rte_correct) / (total * 3)

    # --- Tool usage (25%) ---
    # Agent should have used tools; reward based on credits spent
    initial_budget = 5
    credits_remaining = state.get("tool_credits_remaining", initial_budget)
    tools_used = initial_budget - credits_remaining

    # Expect at least 2 tool calls for hard task (lookup_account + check_incident)
    expected_tool_calls = 2
    tool_score = min(1.0, tools_used / expected_tool_calls)

    # --- VIP handling (20%) ---
    vip_tickets = [
        tid for tid, gt in ground_truth.items()
        if gt.get("vip", False)
    ]
    if vip_tickets:
        resolved = state.get("resolved_tickets", [])
        vip_resolved = sum(1 for tid in vip_tickets if tid in resolved)
        vip_score = vip_resolved / len(vip_tickets)
    else:
        vip_score = 1.0

    # --- Incident response (25%) ---
    expected_incidents = set(
        gt["incident_id"]
        for gt in ground_truth.values()
        if "incident_id" in gt
    )
    incident_tickets = [
        tid for tid, gt in ground_truth.items()
        if "incident_id" in gt
    ]

    inc_score_parts = []

    # Did we track the incidents?
    if expected_incidents:
        tracked = set(state.get("active_incidents", []))
        inc_score_parts.append(len(expected_incidents & tracked) / len(expected_incidents))
    else:
        inc_score_parts.append(1.0)

    # Did we resolve incident tickets?
    if incident_tickets:
        resolved = state.get("resolved_tickets", [])
        inc_resolved = sum(1 for tid in incident_tickets if tid in resolved)
        inc_score_parts.append(inc_resolved / len(incident_tickets))
    else:
        inc_score_parts.append(1.0)

    incident_score = sum(inc_score_parts) / len(inc_score_parts)

    return (
        0.30 * triage_score
        + 0.25 * tool_score
        + 0.20 * vip_score
        + 0.25 * incident_score
    )