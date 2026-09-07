# campaign-agent-langgraph

가맹점 대상 캠페인 챗봇의 라우팅 구조를 LangGraph로 구현한 학습용 프로젝트.

LLM 에이전트에서 "다음 행동을 누가 정하는가"라는 설계 문제를 다룬다. 의미 이해가 필요한 판단은 LLM에 맡기고, 결정적이어야 하는 트리거는 코드로 처리하는 이중 라우팅 구조를 그래프로 표현했다.

## 구조

```
START → condition_agent → keyword_gate → [조건부 분기]
                                           ├→ analytics_agent → respond → END
                                           ├→ campaign_agent  → respond → END
                                           └→ respond → END
```

### 노드별 역할

| 노드 | 역할 |
| --- | --- |
| condition_agent | LLM structured output으로 다음 상태 판정 (핵심 축) |
| keyword_gate | 키워드 매칭으로 분석 도구 개방 여부 결정 (보조 축) |
| analytics_agent | 점포 실적 조회 |
| campaign_agent | 캠페인 초안 생성 |
| respond | 수집된 결과로 최종 응답 생성 |

### 파일별 역할

| 파일 | 역할 |
| --- | --- |
| `state.py` | StateDecision(LLM 출력 스키마), GraphState(노드 공유 상태) |
| `nodes.py` | 노드 함수 5개 |
| `graph.py` | StateGraph 조립, 분기 로직 |
| `main.py` | 터미널 실행 루프 |

## 설계 포인트
- 이중 라우팅. LLM 판단과 키워드 게이트를 함께 돌린다. LLM이 분석 요청을 놓쳐도 발화에 "매출" 같은 키워드가 있으면 게이트가 분석 경로를 열어준다. 반대로 "매출 UP 캠페인 만들어줘"처럼 키워드가 캠페인명에 포함된 경우는 프롬프트의 예외 규칙으로 LLM이 잡아내고, 분기 함수가 LLM 판단을 우선하도록 순서를 잡았다.
- 구조화 출력. 라우팅 판단을 자유 텍스트가 아니라 Pydantic 모델로 받는다. next_state가 정의된 값 밖으로 나갈 수 없어 분기가 안전해진다.
- 상태 지속성. thread_id 기반 체크포인터로 멀티턴 대화가 유지된다. "할인율 20%로 바꿔줘"라는 요청만으로 이전 턴의 캠페인 초안이 갱신된다.

## 실행
bash
conda create -n langgraph-practice python=3.11 -y
conda activate langgraph-practice
pip install langgraph langchain-openai python-dotenv

cp .env.example .env    # OPENAI_API_KEY 입력
python main.py

엔터만 누르면 예시 질의가 순서대로 실행된다. q로 종료.

## 실행 예시

사용자> 강남점 지난주 매출 어때?
  [condition_agent] analytics / 사용자가 매출에 대한 데이터를 묻고 있음
  [keyword_gate] analytics_gate=True
  [analytics_agent] 조회 완료
에이전트> 강남점의 지난주 매출은 1,240만원으로, 전주 대비 8% 감소했습니다.

사용자> 그럼 그 점포에 재방문 캠페인 만들어줘
  [condition_agent] campaign_selection / 사용자가 특정 캠페인을 요청했기 때문입니다
  [keyword_gate] analytics_gate=False
  [campaign_agent] 초안 생성 (할인율 10%)

사용자> 할인율 20%로 바꿔줘
  [condition_agent] condition_change / 이미 만든 캠페인의 할인율 변경 요청
  [keyword_gate] analytics_gate=False
  [campaign_agent] 초안 생성 (할인율 20%)

사용자> 매출 UP 캠페인 만들어줘
  [condition_agent] campaign_selection / 캠페인 생성 요청으로 판단됨
  [keyword_gate] analytics_gate=True
  [campaign_agent] 초안 생성 (할인율 10%)

마지막 케이스에서 키워드 게이트는 열렸지만 LLM 판단이 우선해 캠페인 경로로 갔다. 두 신호가 충돌할 때의 우선순위가 분기 함수의 조건 순서로 보장된다.

## 알려진 한계
respond 노드가 도구 결과를 각색하는 경우가 있다. 실제 서비스라면 도구 산출물을 그대로 출력하고 LLM에는 설명만 맡기거나 검증 단계를 두어야 한다
도구는 더미 구현이다. 실제 데이터 조회나 캠페인 발송은 포함하지 않는다
체크포인터가 MemorySaver라 프로세스 종료 시 상태가 사라진다. 프로덕션에서는 Sqlite, Postgres 등으로 교체한다

## 환경
- Python 3.11, langgraph 1.2.11, langchain-openai 1.6.0