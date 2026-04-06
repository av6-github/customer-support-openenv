import requests


class EnvClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def reset(self, task="triage_sprint"):
        return requests.post(f"{self.base_url}/reset", params={"task": task}).json()

    def step(self, action):
        return requests.post(f"{self.base_url}/step", json=action).json()

    def state(self):
        return requests.get(f"{self.base_url}/state").json()