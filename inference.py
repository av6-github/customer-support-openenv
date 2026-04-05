from client import EnvClient

client = EnvClient()


def run_task(task_name):
    print(f"[START] task={task_name}")

    obs = client.reset(task_name)

    done = False
    steps = 0

    while not done and steps < 5:
        action = {
            "action_type": "submit"
        }

        obs = client.step(action)
        done = obs["done"]
        steps += 1

        print(f"[STEP] step={steps}")

    print(f"[END] task={task_name} score=0.00")


if __name__ == "__main__":
    for task in ["triage_sprint", "queue_pressure", "incident_cascade"]:
        run_task(task)