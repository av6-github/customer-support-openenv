import os
from client import EnvClient
from agent.agent import SupportAgent
from dotenv import load_dotenv

load_dotenv()

# -----------------------------
# CONFIG
# -----------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

BASE_URL = "http://localhost:8000"

TASKS = [
    "triage_sprint",
    "churn_sla",
    "clustering",
    "incident_cascade",
    "policy_conflict",
]


# -----------------------------
# RUN SINGLE TASK
# -----------------------------
def run_task(task_name, agent, client):

    print(f"[START] task={task_name} env=customer-support model={MODEL_NAME}", flush=True)

    obs = client.reset(task_name)
    agent.set_task(task_name)

    done = False
    step = 0
    total_reward = 0.0
    rewards = []

    while not done:
        action = agent.get_action(obs)

        step_response = client.step(action)
        obs = step_response["observation"]
        reward = step_response["reward"]

        step += 1
        total_reward += reward
        rewards.append(reward)

        done = step_response["done"]
        
        done_val = str(done).lower()
        error_val = "null"  # No error tracking necessary for this deterministic baseline
        action_str = f"{action['action_type']}"

        print(f"[STEP] step={step} action={action_str} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

    # -----------------------------
    # FINAL SCORE
    # -----------------------------
    score = max(0.0, min(total_reward, 1.0))
    success = score >= 0.1
    success_val = str(success).lower()
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)

    print(f"[END] success={success_val} steps={step} score={score:.2f} rewards={rewards_str}", flush=True)

    return score


# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":

    client = EnvClient(BASE_URL)
    agent = SupportAgent(api_key=HF_TOKEN, model=MODEL_NAME, base_url=API_BASE_URL)

    all_scores = []

    for task in TASKS:
        score = run_task(task, agent, client)
        all_scores.append(score)

    avg_score = sum(all_scores) / len(all_scores)

    print(f"\nFINAL AVERAGE SCORE: {avg_score:.2f}")