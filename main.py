"""터미널에서 멀티턴으로 그래프를 돌려 본다."""

from langchain_core.messages import HumanMessage

from graph import build_graph

EXAMPLES = [
    "강남점 지난주 매출 어때?",
    "그럼 그 점포에 재방문 캠페인 만들어줘",
    "할인율 20%로 바꿔줘",
]


def main():
    graph = build_graph()
    config = {"configurable": {"thread_id": "demo-session"}}

    print("캠페인 에이전트 (LangGraph 재현). 'q' 로 종료, 엔터만 치면 예시 질의 실행\n")
    idx = 0

    while True:
        user = input("사용자> ").strip()
        if user.lower() in ("q", "quit", "exit"):
            break
        if not user:
            if idx >= len(EXAMPLES):
                print("예시가 끝났습니다. 직접 입력해 보세요.")
                continue
            user = EXAMPLES[idx]
            idx += 1
            print(f"사용자> {user}")

        result = graph.invoke(
            {"messages": [HumanMessage(content=user)], "discount_rate": 10},
            config=config,
        )
        print(f"에이전트> {result['messages'][-1].content}\n")


if __name__ == "__main__":
    main()