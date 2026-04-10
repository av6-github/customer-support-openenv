from server.support_ops_env_environment import SupportOpsEnvironment

class SessionManager:
    def __init__(self):
        self._sessions = {}

    def get_env(self, session_id: str) -> SupportOpsEnvironment:
        if session_id not in self._sessions:
            self._sessions[session_id] = SupportOpsEnvironment()
        return self._sessions[session_id]

    def remove_env(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]
