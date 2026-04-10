from server.support_ops_env_environment import SupportOpsEnvironment

def test_full_episode_random_actions():
    """Reset → 10 steps → done → score bounds check"""
    env = SupportOpsEnvironment()
    obs = env.reset(task="triage_sprint")
   
    for step in range(10):
        result = env.step({"action_type": "submit"})
        reward = result["reward"]
        done = result["done"]
        assert -1 <= reward <= 1
        if done:
            break
