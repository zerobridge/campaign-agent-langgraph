"""그래프 전체가 공유하는 상태 정의.
ex. AWS환경의 챗봇에서 DynamoDB에 저장하던 세션 상태를 LangGraph의 State로 옮긴 것에 해당한다.
"""

from typing import Annotated, Literal, Optional, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

class StateDecision(BaseModel):
    """상태 판단 에이전트의 structured output 스키마.

    ex. Pydantic 구조화 출력으로 라우팅 판단을 받던 방식과 동일하다.
    """

    is_campaign_workflow: bool = Field(
        description="캠페인 생성/수정 흐름이면 True, 실적 분석 등 조회성이면 False"
    )
    next_state: Literal[
        "analytics", "campaign_selection", "condition_change", "reset"
    ] = Field(description="다음에 진입할 상태")
    reason: str = Field(description="그렇게 판단한 한 줄 근거")
    store_name: Optional[str] = Field(
        default=None, description="발화에서 식별된 점포명, 없으면 null"
    )
    discount_rate: Optional[int] = Field(
        default=None, description="조건 변경 요청에 포함된 할인율(%), 없으면 null"
    )

class GraphState(TypedDict):
    """노드 사이를 흐르는 상태.

    messages 는 add_messages 리듀서를 써서 노드가 반환한 메시지가
    덮어쓰기가 아니라 누적되도록 한다.
    """

    messages: Annotated[list[AnyMessage], add_messages]
    decision: Optional[StateDecision]
    analytics_gate: bool          # 키워드 게이트 통과 여부
    tool_result: Optional[str]    # 도구 실행 결과
    campaign_draft: Optional[str] # 생성된 캠페인 초안
    discount_rate: int            # 현재 캠페인 조건