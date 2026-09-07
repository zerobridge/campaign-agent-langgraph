"""StateGraph 조립.

노드와 조건부 엣지로 제어 흐름을 명시적으로 그린다는 점이
모델이 루프를 주도하는 방식과의 가장 큰 차이다.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from nodes import (
    analytics_agent,
    campaign_agent,
    condition_agent,
    keyword_gate,
    respond,
)
from state import GraphState


def route_after_gate(state: GraphState) -> str:
    """상태 판단 결과와 키워드 게이트를 함께 보고 다음 노드를 고른다."""
    decision = state["decision"]

    if decision.next_state == "reset":
        return "respond"

    if decision.next_state in ("campaign_selection", "condition_change"):
        return "campaign_agent"

    # analytics 로 판단됐거나, LLM 이 놓쳤어도 키워드 게이트가 열렸으면 분석 경로
    if decision.next_state == "analytics" or state["analytics_gate"]:
        return "analytics_agent"

    return "respond"


def build_graph():
    builder = StateGraph(GraphState)

    builder.add_node("condition_agent", condition_agent)
    builder.add_node("keyword_gate", keyword_gate)
    builder.add_node("analytics_agent", analytics_agent)
    builder.add_node("campaign_agent", campaign_agent)
    builder.add_node("respond", respond)

    builder.add_edge(START, "condition_agent")
    builder.add_edge("condition_agent", "keyword_gate")

    builder.add_conditional_edges(
        "keyword_gate",
        route_after_gate,
        {
            "analytics_agent": "analytics_agent",
            "campaign_agent": "campaign_agent",
            "respond": "respond",
        },
    )

    builder.add_edge("analytics_agent", "respond")
    builder.add_edge("campaign_agent", "respond")
    builder.add_edge("respond", END)

    # 세션 상태 저장. 실무의 DynamoDB 대화 이력 저장에 해당한다.
    return builder.compile(checkpointer=MemorySaver())