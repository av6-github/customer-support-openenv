from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from server.support_ops_env_environment import SupportOpsEnvironment
from models import SupportOpsAction
import json

app = FastAPI()

env = SupportOpsEnvironment()


# -----------------------------
# HTTP ENDPOINTS (backward-compatible)
# -----------------------------

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


# -----------------------------
# WEBSOCKET ENDPOINT
# -----------------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    # Each WebSocket connection gets its own isolated environment
    ws_env = SupportOpsEnvironment()

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)

            action = msg.get("action")

            if action == "reset":
                task = msg.get("task", "triage_sprint")
                result = ws_env.reset(task)
                await ws.send_json({"type": "reset", "data": result})

            elif action == "step":
                step_action = msg.get("data", {})
                result = ws_env.step(step_action)
                await ws.send_json({"type": "step", "data": result})

            elif action == "state":
                result = ws_env.state()
                await ws.send_json({"type": "state", "data": result})

            else:
                await ws.send_json({"type": "error", "message": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        pass  # Client disconnected — environment is garbage collected


# -----------------------------
# ENTRY POINT
# -----------------------------

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()