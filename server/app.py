from fastapi import FastAPI
from server.support_ops_env_environment import SupportOpsEnvironment

app = FastAPI()

env = SupportOpsEnvironment()


@app.get("/")
def root():
    return {"message": "Support Ops Environment Running"}


@app.post("/reset")
def reset(task: str = "triage_sprint"):
    return env.reset(task)


@app.post("/step")
def step(action: dict):
    return env.step(action)


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


main()