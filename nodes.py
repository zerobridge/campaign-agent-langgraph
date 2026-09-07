"""그래프의 각 노드.

- condition_agent : LLM structured output 으로 상태를 판단 (핵심 축)
- keyword_gate    : 키워드 매칭으로 분석 도구 활성화 여부 결정 (보조 축)
- analytics_agent : 점포 실적 조회 도구 (더미)
- campaign_agent  : 캠페인 초안 생성 도구 (더미)
- respond         : 수집된 결과로 최종 응답 생성
"""

import os

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from state import GraphState, StateDecision

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 실무에서 Parameter Store 로 외부화했던 키워드 셋에 해당한다.
ANALYTICS_KEYWORDS = ["매출", "실적", "추이", "비교", "반응률", "객수"]

ROUTING_PROMPT = """너는 가맹점 캠페인 챗봇의 상태 판단기다.
사용자 발화와 지금까지의 대화를 보고 다음 상태를 판정한다.

판단 우선순위:
1) 이미 만든 캠페인의 조건(할인율, 기간, 톤)을 바꾸라는 요청이면 condition_change
2) 캠페인을 만들거나 추천해 달라는 요청이면 campaign_selection
3) 매출/실적/추이 등 데이터를 묻는 조회성 질의면 analytics
4) 처음부터 다시 하자는 요청이면 reset

주의: "매출 UP 캠페인 만들어줘" 처럼 분석 키워드가 캠페인명에 들어간 경우는
analytics 가 아니라 campaign_selection 이다.
"""


def condition_agent(state: GraphState) -> dict:
    """LLM 이 구조화 출력으로 다음 상태를 판단한다."""
    structured_llm = llm.with_structured_output(StateDecision)
    decision = structured_llm.invoke(
        [SystemMessage(content=ROUTING_PROMPT)] + state["messages"]
    )
    print(f"  [condition_agent] {decision.next_state} / {decision.reason}")
    updates: dict = {"decision": decision}
    if decision.discount_rate is not None:
        updates["discount_rate"] = decision.discount_rate
    return updates


def keyword_gate(state: GraphState) -> dict:
    """LLM 과 별개로, 문자열 매칭만으로 분석 도구 개방 여부를 결정한다.

    확률적 판단이 흔들려도 명시적 신호가 있으면 도구를 열어 주는 안전핀.
    """
    last_user = state["messages"][-1].content
    gate = any(k in last_user for k in ANALYTICS_KEYWORDS)
    print(f"  [keyword_gate] analytics_gate={gate}")
    return {"analytics_gate": gate}


def analytics_agent(state: GraphState) -> dict:
    """점포 실적 조회 (실무의 Athena 쿼리 자리)."""
    store = (state["decision"].store_name if state["decision"] else None) or "전체 점포"
    result = f"{store} 최근 7일 매출 1,240만원, 전주 대비 8% 감소, 객수 3,120명"
    print(f"  [analytics_agent] 조회 완료")
    return {"tool_result": result}


def campaign_agent(state: GraphState) -> dict:
    """캠페인 초안 생성 (실무의 캠페인 생성 도구 자리)."""
    rate = state.get("discount_rate") or 10
    store = (state["decision"].store_name if state["decision"] else None) or "대상 점포"
    draft = (
        f"[{store}] 재방문 유도 캠페인\n"
        f"  - 대상: 최근 30일 미방문 고객\n"
        f"  - 혜택: 전 메뉴 {rate}% 할인\n"
        f"  - 기간: 발송일로부터 7일"
    )
    print(f"  [campaign_agent] 초안 생성 (할인율 {rate}%)")
    return {"campaign_draft": draft}


def respond(state: GraphState) -> dict:
    """수집된 도구 결과로 최종 응답을 만든다."""
    context = []
    if state.get("tool_result"):
        context.append(f"조회 결과: {state['tool_result']}")
    if state.get("campaign_draft"):
        context.append(f"캠페인 초안:\n{state['campaign_draft']}")

    if not context:
        return {"messages": [AIMessage(content="처음부터 다시 시작하겠습니다. 무엇을 도와드릴까요?")]}

    system = SystemMessage(
        content="너는 가맹점주를 돕는 캠페인 어시스턴트다. "
        "아래 근거만 사용해 두세 문장으로 간결히 답한다.\n\n" + "\n".join(context)
    )
    answer = llm.invoke([system] + state["messages"])
    return {"messages": [answer]}