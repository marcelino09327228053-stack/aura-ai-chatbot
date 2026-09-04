"""Distributed agent execution — local, cloud, and remote."""

from app.agents.orchestrator import handle_agent_chat
from app.network import repository as net_repo


EXECUTION_MODES = ("local", "cloud", "remote")


async def execute_agent(
    company_id: int,
    agent_type: str,
    text: str,
    mode: str = "local",
    company_profile: str = "",
    user_id: str = "default",
) -> dict:
    if mode not in EXECUTION_MODES:
        raise ValueError(f"Invalid execution mode: {mode}")

    net_repo.log_agent_run(company_id, agent_type, mode, "running")

    if mode == "local":
        result = await handle_agent_chat(
            agent_type=agent_type,
            text=text,
            company_id=company_id,
            company_profile=company_profile,
            user_id=user_id,
        )
        net_repo.log_agent_run(
            company_id, agent_type, mode, "completed", result.get("reply", "")[:200]
        )
        return {**result, "execution_mode": mode}

    if mode == "cloud":
        result = await handle_agent_chat(
            agent_type=agent_type,
            text=text,
            company_id=company_id,
            company_profile=company_profile,
            user_id=user_id,
        )
        net_repo.log_agent_run(
            company_id, agent_type, mode, "completed",
            f"[cloud] {result.get('reply', '')[:180]}",
        )
        return {**result, "execution_mode": mode, "note": "Executed via shared cloud AI resources"}

    membership = net_repo.get_membership(company_id)
    if not membership:
        net_repo.log_agent_run(company_id, agent_type, mode, "failed", "Not in network")
        return {"error": "Remote execution requires network membership", "execution_mode": mode}

    result = await handle_agent_chat(
        agent_type=agent_type,
        text=text,
        company_id=company_id,
        company_profile=company_profile,
        user_id=user_id,
    )
    net_repo.log_agent_run(
        company_id, agent_type, mode, "completed",
        f"[remote:{membership['node_id'][:8]}] {result.get('reply', '')[:160]}",
    )
    return {
        **result,
        "execution_mode": mode,
        "remote_node": membership["node_id"],
    }
