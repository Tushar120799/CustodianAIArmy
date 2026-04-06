from src.agents.agent_manager import AgentManager
am = AgentManager()
for a in am.agents.values():
    print(a.name)
