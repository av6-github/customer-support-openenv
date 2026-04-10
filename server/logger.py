import json
from datetime import datetime

class MetricsLogger:
    def __init__(self, task_name):
        self.task = task_name
        self.metrics = {"task": task_name, "steps": []}
   
    def log_step(self, step_num, action, reward, llm_tokens, tool_calls):
        self.metrics["steps"].append({
            "step": step_num,
            "action": action,
            "reward": reward,
            "llm_tokens": llm_tokens,
            "tool_calls": tool_calls,
            "timestamp": datetime.utcnow().isoformat()
        })
   
    def to_json(self):
        return json.dumps(self.metrics, indent=2)

class AgentLogger:
    def __init__(self):
        self.decisions = []

    def log_decision(self, decision_str: str):
        self.decisions.append({
            "decision": decision_str,
            "timestamp": datetime.utcnow().isoformat()
        })

    def get_logs(self):
        return self.decisions
