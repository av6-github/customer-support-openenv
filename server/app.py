from fastapi import FastAPI
from server.support_ops_env_environment import SupportOpsEnvironment
from models import SupportOpsAction

app = FastAPI()

env = SupportOpsEnvironment()


@app.get("/")
def root():
    return {"message": "Support Ops Environment Running"}


@app.post("/reset")
def reset(task: str = "triage_sprint"):
    return env.reset(task)


@app.post("/step")
def step(action: SupportOpsAction):
    return env.step(action.model_dump() if hasattr(action, 'model_dump') else action.dict())


@app.get("/state")
def get_state():
    return env.state()


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()