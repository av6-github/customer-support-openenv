from models import SupportOpsObservation, SupportOpsState
from typing import Dict


class SupportOpsEnvironment:

    def __init__(self):
        self.state = SupportOpsState(tickets={})

    def reset(self, task: str = "triage_sprint") -> Dict:
        self.state = SupportOpsState(tickets={})

        return SupportOpsObservation(
            tickets=[],
            step_count=0,
            max_steps=20,
            tool_credits_remaining=5,
            queue_health=1.0,
            sla_deadlines={},
            visible_churn_risk={},
            reward=0.0,
            done=False
        ).dict()

    def step(self, action: Dict) -> Dict:
        self.state.step_count += 1

        done = self.state.step_count >= self.state.max_steps

        return SupportOpsObservation(
            tickets=[],
            step_count=self.state.step_count,
            max_steps=self.state.max_steps,
            tool_credits_remaining=self.state.tool_credits_remaining,
            queue_health=self.state.queue_health,
            sla_deadlines={},
            visible_churn_risk={},
            reward=0.0,
            done=done
        ).dict()