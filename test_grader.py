from server.support_ops_env_environment import SupportOpsEnvironment


def run_perfect_episode(task_name):
    """Run a perfect episode using ground truth for the given task."""
    env = SupportOpsEnvironment()
    obs = env.reset(task_name)
    gt = env._ground_truth
    done = False
    total_reward = 0.0
    step = 0
    used_tools = set()

    while not done:
        tickets = obs["tickets"]

        # Find first unresolved ticket
        ticket = None
        for t in tickets:
            if t["status"] != "resolved":
                ticket = t
                break

        # --- Phase: Duplicate merge (clustering) ---
        if task_name == "clustering":
            for tid, g in gt.items():
                if "duplicate_of" in g and tid not in env._state.duplicates:
                    result = env.step({
                        "action_type": "merge_duplicate",
                        "ticket_id": tid,
                        "duplicate_ticket_id": g["duplicate_of"]
                    })
                    step += 1
                    total_reward += result["reward"]
                    done = result["done"]
                    obs = result["observation"]
                    if done:
                        break

        if done:
            break

        # --- Phase: Tool usage (incident_cascade) ---
        if task_name == "incident_cascade" and env._state.tool_credits_remaining > 0:
            for tid, g in gt.items():
                if "incident_id" in g and f"inc_{tid}" not in used_tools:
                    used_tools.add(f"inc_{tid}")
                    result = env.step({
                        "action_type": "check_incident",
                        "incident_id": g["incident_id"]
                    })
                    step += 1
                    total_reward += result["reward"]
                    done = result["done"]
                    obs = result["observation"]
                    if done:
                        break

                if g.get("fraud_flag") and f"acc_{tid}" not in used_tools:
                    used_tools.add(f"acc_{tid}")
                    result = env.step({
                        "action_type": "lookup_account",
                        "account_id": tid
                    })
                    step += 1
                    total_reward += result["reward"]
                    done = result["done"]
                    obs = result["observation"]
                    if done:
                        break

        if done:
            break

        if not ticket:
            result = env.step({"action_type": "submit"})
            total_reward += result["reward"]
            done = result["done"]
            break

        tid = ticket["ticket_id"]
        g = gt[tid]

        # Step 1: categorize
        result = env.step({
            "action_type": "categorize",
            "ticket_id": tid,
            "category": g["category"]
        })
        step += 1
        total_reward += result["reward"]
        done = result["done"]
        obs = result["observation"]
        if done:
            break

        # Step 2: priority
        result = env.step({
            "action_type": "set_priority",
            "ticket_id": tid,
            "priority": g["priority"]
        })
        step += 1
        total_reward += result["reward"]
        done = result["done"]
        obs = result["observation"]
        if done:
            break

        # Step 3: route
        result = env.step({
            "action_type": "route",
            "ticket_id": tid,
            "queue": g["queue"]
        })
        step += 1
        total_reward += result["reward"]
        done = result["done"]
        obs = result["observation"]
        if done:
            break

        # Step 4: resolve
        result = env.step({
            "action_type": "resolve",
            "ticket_id": tid
        })
        step += 1
        total_reward += result["reward"]
        done = result["done"]
        obs = result["observation"]

    print(f"[{task_name}] steps={step} total_reward={total_reward:.4f}")
    assert total_reward <= 1.5, f"FAIL: reward {total_reward:.4f} is way too high!"
    return total_reward


if __name__ == "__main__":
    print("=" * 50)
    print("PERFECT EPISODE TESTS")
    print("=" * 50)

    tasks = ["triage_sprint", "clustering", "incident_cascade"]
    scores = {}

    for task in tasks:
        try:
            score = run_perfect_episode(task)
            scores[task] = score
            status = "✅ PASS" if 0.0 <= score <= 1.2 else "❌ FAIL (out of range)"
            print(f"  {status}: {task} → {score:.4f}")
        except Exception as e:
            print(f"  ❌ ERROR: {task} → {e}")
            scores[task] = -1

    print()
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for task, score in scores.items():
        print(f"  {task}: {score:.4f}")

    valid = [s for s in scores.values() if s >= 0]
    if valid:
        avg = sum(valid) / len(valid)
        print(f"\n  Average: {avg:.4f}")