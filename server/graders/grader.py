def grade_triage_sprint(state, ground_truth):
    """
    Task 1 — Pure triage accuracy.
    Weights: category 35%, priority 30%, routing 35%.
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


def grade_churn_sla(state, ground_truth):
    """
    Task 2 — Churn Control + SLA Management.
    Weights:
      - High churn resolved  30%
      - SLA compliance       25%
      - Efficiency           15%
      - Triage correctness   15%
      - Completion rate      15%
    """
    total = len(ground_truth)
    if total == 0:
        return 0.0

    resolved = state.get("resolved_tickets", [])

    # --- High churn resolved (30%) ---
    high_churn = [tid for tid, gt in ground_truth.items() if gt.get("churn_risk", 0) >= 0.7]
    if high_churn:
        hc_resolved = sum(1 for tid in high_churn if tid in resolved)
        hc_score = hc_resolved / len(high_churn)
    else:
        hc_score = 1.0

    # --- SLA compliance (25%) ---
    # A ticket is SLA-compliant if it was resolved before step_count exceeded its sla_deadline
    sla_tickets = [tid for tid, gt in ground_truth.items() if gt.get("sla_deadline")]
    if sla_tickets:
        sla_compliant = 0
        for tid in sla_tickets:
            if tid in resolved:
                sla_compliant += 1  # resolved = compliant (we assume resolve happened before violation)
        sla_score = sla_compliant / len(sla_tickets)
    else:
        sla_score = 1.0

    # --- Efficiency (15%) ---
    max_steps = state.get("max_steps", 35)
    steps_used = state.get("step_count", max_steps)
    efficiency_score = max(0.0, 1.0 - (steps_used / max_steps))

    # --- Triage correctness (15%) ---
    cat_correct = sum(1 for tid, gt in ground_truth.items()
                      if state["categorized"].get(tid) == gt["category"])
    pri_correct = sum(1 for tid, gt in ground_truth.items()
                      if state["prioritized"].get(tid) == gt["priority"])
    rte_correct = sum(1 for tid, gt in ground_truth.items()
                      if state["routed"].get(tid) == gt["queue"])
    triage_score = (cat_correct + pri_correct + rte_correct) / (total * 3)

    # --- Completion rate (15%) ---
    completion_score = len(resolved) / total

    return (
        0.30 * hc_score
        + 0.25 * sla_score
        + 0.15 * efficiency_score
        + 0.15 * triage_score
        + 0.15 * completion_score
    )


def grade_clustering(state, ground_truth):
    """
    Task 3 — Duplicate + Semantic Clustering.
    Weights:
      - Clustering accuracy     35%
      - Merge correctness       25%
      - Redundant work avoided  20%
      - Resolution correctness  20%
    """
    total = len(ground_truth)
    if total == 0:
        return 0.0

    resolved = state.get("resolved_tickets", [])
    clusters = state.get("clusters", {})

    # --- Clustering accuracy (35%) ---
    # Expected cluster pairs: tickets that share a cluster_id should be merged
    expected_pairs = []
    cluster_groups = {}
    for tid, gt in ground_truth.items():
        cid = gt.get("cluster_id")
        if cid:
            cluster_groups.setdefault(cid, []).append(tid)

    for cid, members in cluster_groups.items():
        if len(members) >= 2:
            root = members[0]
            for child in members[1:]:
                expected_pairs.append((child, root))

    if expected_pairs:
        correct_merges = 0
        for child, expected_root in expected_pairs:
            actual_parent = clusters.get(child)
            if actual_parent:
                # Check if the actual parent is in the same cluster
                actual_cluster = ground_truth.get(actual_parent, {}).get("cluster_id")
                child_cluster = ground_truth.get(child, {}).get("cluster_id")
                if actual_cluster and child_cluster and actual_cluster == child_cluster:
                    correct_merges += 1
        clustering_score = correct_merges / len(expected_pairs)
    else:
        clustering_score = 1.0

    # --- Merge correctness (25%) ---
    # Any merge that links tickets from different clusters is incorrect
    total_merges = len(clusters)
    if total_merges > 0:
        incorrect = 0
        for child, parent in clusters.items():
            child_cid = ground_truth.get(child, {}).get("cluster_id")
            parent_cid = ground_truth.get(parent, {}).get("cluster_id")
            if child_cid != parent_cid:
                incorrect += 1
        merge_score = 1.0 - (incorrect / total_merges)
    else:
        merge_score = 0.0 if expected_pairs else 1.0

    # --- Redundant work avoided (20%) ---
    # For each cluster, only ONE ticket should be fully triaged/resolved
    # Resolving multiple tickets in the same cluster is wasteful
    redundancy_penalties = 0
    redundancy_total = 0
    for cid, members in cluster_groups.items():
        if len(members) >= 2:
            resolved_in_cluster = [tid for tid in members if tid in resolved]
            redundancy_total += 1
            if len(resolved_in_cluster) <= 1:
                # Good: resolved at most one
                pass
            else:
                redundancy_penalties += 1

    if redundancy_total > 0:
        redundancy_score = 1.0 - (redundancy_penalties / redundancy_total)
    else:
        redundancy_score = 1.0

    # --- Resolution correctness (20%) ---
    cat_correct = sum(1 for tid, gt in ground_truth.items()
                      if state["categorized"].get(tid) == gt["category"])
    triage_score = cat_correct / total

    return (
        0.35 * clustering_score
        + 0.25 * merge_score
        + 0.20 * redundancy_score
        + 0.20 * triage_score
    )


def grade_incident_cascade(state, ground_truth):
    """
    Task 4 — Incident Cascade + System Stabilization.
    Weights:
      - Incident detection        25%
      - Severity prioritization   20%
      - System health maintained  20%
      - Efficiency                15%
      - Ticket correctness        20%
    """
    total = len(ground_truth)
    if total == 0:
        return 0.0

    resolved = state.get("resolved_tickets", [])

    # --- Incident detection (25%) ---
    expected_incidents = set(
        gt["incident_id"]
        for gt in ground_truth.values()
        if gt.get("incident_id")
    )
    if expected_incidents:
        tracked = set(state.get("active_incidents", []))
        detection_score = len(expected_incidents & tracked) / len(expected_incidents)
    else:
        detection_score = 1.0

    # --- Severity prioritization (20%) ---
    # Critical incidents should be resolved before high/medium/low
    incident_tickets = [
        (tid, gt.get("incident_severity", "low"))
        for tid, gt in ground_truth.items()
        if gt.get("incident_id")
    ]
    if incident_tickets:
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_by_severity = sorted(incident_tickets, key=lambda x: severity_order.get(x[1], 3))
        # Check if critical incidents were resolved
        critical_resolved = sum(
            1 for tid, sev in sorted_by_severity
            if sev == "critical" and tid in resolved
        )
        critical_total = sum(1 for _, sev in sorted_by_severity if sev == "critical")
        severity_score = critical_resolved / critical_total if critical_total > 0 else 1.0
    else:
        severity_score = 1.0

    # --- System health maintained (20%) ---
    system_health = state.get("system_health", 0.0)
    health_score = max(0.0, system_health)

    # --- Efficiency (15%) ---
    max_steps = state.get("max_steps", 35)
    steps_used = state.get("step_count", max_steps)
    efficiency_score = max(0.0, 1.0 - (steps_used / max_steps))

    # --- Ticket correctness (20%) ---
    cat_correct = sum(1 for tid, gt in ground_truth.items()
                      if state["categorized"].get(tid) == gt["category"])
    pri_correct = sum(1 for tid, gt in ground_truth.items()
                      if state["prioritized"].get(tid) == gt["priority"])
    rte_correct = sum(1 for tid, gt in ground_truth.items()
                      if state["routed"].get(tid) == gt["queue"])
    triage_score = (cat_correct + pri_correct + rte_correct) / (total * 3)

    return (
        0.25 * detection_score
        + 0.20 * severity_score
        + 0.20 * health_score
        + 0.15 * efficiency_score
        + 0.20 * triage_score
    )


def grade_policy_conflict(state, ground_truth):
    """
    Task 5 — Policy Conflict + Risk + Compliance.
    Weights:
      - Policy correctness   30%
      - Risk avoidance       25%
      - Tool usage           15%
      - VIP handling         15%
      - Resolution success   15%
    """
    total = len(ground_truth)
    if total == 0:
        return 0.0

    resolved = state.get("resolved_tickets", [])

    # --- Policy correctness (30%) ---
    # Fraud tickets must NOT be categorized as billing (implies refund approval)
    fraud_tickets = [tid for tid, gt in ground_truth.items() if gt.get("fraud_flag")]
    policy_violations = 0
    if fraud_tickets:
        for tid in fraud_tickets:
            cat = state["categorized"].get(tid)
            if cat == "billing":  # Refund approved for fraudster = violation
                policy_violations += 1
        policy_score = 1.0 - (policy_violations / len(fraud_tickets))
    else:
        policy_score = 1.0

    # --- Risk avoidance (25%) ---
    # For fraud+VIP combo tickets, the safest action is to NOT resolve (escalate instead)
    risky_tickets = [tid for tid, gt in ground_truth.items()
                     if gt.get("fraud_flag") and gt.get("vip")]
    if risky_tickets:
        bad_resolutions = sum(1 for tid in risky_tickets if tid in resolved)
        risk_score = 1.0 - (bad_resolutions / len(risky_tickets))
    else:
        risk_score = 1.0

    # --- Tool usage (15%) ---
    initial_budget = 5
    credits_remaining = state.get("tool_credits_remaining", initial_budget)
    tools_used = initial_budget - credits_remaining
    expected_tool_calls = len(ground_truth)  # Should lookup each ticket's account
    tool_score = min(1.0, tools_used / max(1, expected_tool_calls))

    # --- VIP handling (15%) ---
    vip_tickets = [tid for tid, gt in ground_truth.items()
                   if gt.get("vip") and not gt.get("fraud_flag")]
    if vip_tickets:
        vip_resolved = sum(1 for tid in vip_tickets if tid in resolved)
        vip_score = vip_resolved / len(vip_tickets)
    else:
        vip_score = 1.0

    # --- Resolution success (15%) ---
    # Non-fraud tickets should be resolved
    safe_tickets = [tid for tid, gt in ground_truth.items() if not gt.get("fraud_flag")]
    if safe_tickets:
        safe_resolved = sum(1 for tid in safe_tickets if tid in resolved)
        resolution_score = safe_resolved / len(safe_tickets)
    else:
        resolution_score = 1.0

    return (
        0.30 * policy_score
        + 0.25 * risk_score
        + 0.15 * tool_score
        + 0.15 * vip_score
        + 0.15 * resolution_score
    )