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

BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:8000")

# Single task per run — evaluator calls this script once per task
TASK_NAME = os.getenv("TASK_NAME", "triage_sprint")
ENV_NAME = "customer-support-openenv"


# -----------------------------
# RUN SINGLE TASK
# -----------------------------
def run_task(task_name, agent, client):

    print(f"[START] task={task_name} env={ENV_NAME} model={MODEL_NAME}", flush=True)

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
        error_val = step_response.get("error") or "null"
        action_str = f"{action['action_type']}"

        print(f"[STEP] step={step} action={action_str} reward={reward:.3f} done={done_val} error={error_val}", flush=True)

    # -----------------------------
    # FINAL SCORE
    # -----------------------------
    score = max(0.0, min(total_reward, 1.0))
    success = score >= 0.1
    success_val = str(success).lower()
    rewards_str = ",".join(f"{r:.3f}" for r in rewards)

    print(f"[END] success={success_val} steps={step} score={score:.3f} rewards={rewards_str}", flush=True)

    return score


# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":

    client = EnvClient(BASE_URL)
    agent = SupportAgent(api_key=HF_TOKEN, model=MODEL_NAME, base_url=API_BASE_URL)

    score = run_task(TASK_NAME, agent, client)