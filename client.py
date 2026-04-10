import requests
import json
import uuid

try:
    import websockets
    import asyncio
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False


class EnvClient:
    """HTTP-based client for the Support Ops environment."""

    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session_id = str(uuid.uuid4())

    def reset(self, task="triage_sprint"):
        return requests.post(f"{self.base_url}/reset", params={"task": task, "session_id": self.session_id}).json()

    def step(self, action):
        return requests.post(f"{self.base_url}/step", json=action, params={"session_id": self.session_id}).json()

    def state(self):
        return requests.get(f"{self.base_url}/state", params={"session_id": self.session_id}).json()


class WebSocketEnvClient:
    """
    WebSocket-based client for the Support Ops environment.
    Provides persistent connection with lower latency per step.
    Each connection gets its own isolated environment instance.
    """

    def __init__(self, base_url="http://localhost:8000"):
        # Convert http(s) to ws(s) URL
        ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
        self.ws_url = f"{ws_url}/ws"
        self._ws = None
        self._loop = None

    def connect(self):
        """Establish WebSocket connection."""
        self._loop = asyncio.new_event_loop()
        self._ws = self._loop.run_until_complete(
            websockets.connect(self.ws_url)
        )
        return self

    def close(self):
        """Close WebSocket connection."""
        if self._ws:
            self._loop.run_until_complete(self._ws.close())
        if self._loop:
            self._loop.close()

    def __enter__(self):
        return self.connect()

    def __exit__(self, *args):
        self.close()

    def _send_and_receive(self, message):
        """Send a message and wait for response."""
        self._loop.run_until_complete(self._ws.send(json.dumps(message)))
        raw = self._loop.run_until_complete(self._ws.recv())
        return json.loads(raw)["data"]

    def reset(self, task="triage_sprint"):
        return self._send_and_receive({"action": "reset", "task": task})

    def step(self, action):
        return self._send_and_receive({"action": "step", "data": action})

    def state(self):
        return self._send_and_receive({"action": "state"})