import pytest
from server.support_ops_env_environment import SupportOpsEnvironment

class TestTaskReset:
    def test_triage_reset_produces_valid_observation(self):
        env = SupportOpsEnvironment()
        obs = env.reset(task="triage_sprint")
        assert len(obs["tickets"]) > 0
        assert obs["step_count"] == 0
        assert obs["max_steps"] > 0
       
    def test_churn_management_reset_has_churn_risk(self):
        env = SupportOpsEnvironment()
        obs = env.reset(task="churn_sla")
        assert "visible_churn_risk" in obs
