import os
from client import EnvClient
from agent.agent import SupportAgent


# -----------------------------
# CONFIG
# -----------------------------
API_KEY = os.getenv("OPENAI_API_KEY")  # MUST be set
BASE_URL = "http://localhost:8000"

TASKS = [
    "triage_sprint",
    "queue_pressure",
    "incident_cascade"
]


# -----------------------------
# RUN SINGLE TASK
# -----------------------------
def run_task(task_name, agent, client):

    print(f"[START] task={task_name}")

    obs = client.reset(task_name)
    agent.set_task(task_name)

    done = False
    step = 0
    total_reward = 0.0

    while not done:

        action = agent.get_action(obs)

        step_response = client.step(action)
        obs = step_response["observation"]

        step += 1
        total_reward += step_response["reward"]

        print(f"[STEP] step={step} action={action['action_type']} reward={step_response['reward']:.3f}")

        done = step_response["done"]

    # -----------------------------
    # FINAL SCORE
    # -----------------------------
    score = max(0.0, min(total_reward, 1.0))

    print(f"[END] task={task_name} score={score:.2f}")

    return score


# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":

    if not API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    client = EnvClient(BASE_URL)
    agent = SupportAgent(API_KEY)

    all_scores = []

    for task in TASKS:
        score = run_task(task, agent, client)
        all_scores.append(score)

    avg_score = sum(all_scores) / len(all_scores)

    print(f"\nFINAL AVERAGE SCORE: {avg_score:.2f}")