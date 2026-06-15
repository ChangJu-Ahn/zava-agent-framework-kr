# Microsoft Agent Framework GA 마이그레이션 보고서

## 1. 개요

이 문서는 Zava 의류 컨셉 분석 데모를 **Microsoft Agent Framework의 GA 이전 베타 버전
(`1.0.0b251001`)** 에서 **현재 시점의 최신 GA 버전(`1.8.1`)** 으로 마이그레이션한
작업의 진행 사항, 방법, 결과를 정리한 것입니다.

| 항목 | 마이그레이션 전 | 마이그레이션 후 |
| --- | --- | --- |
| `agent-framework` (메타) | `1.0.0b251001` | 제거 (아래 설명 참고) |
| `agent-framework-core` | `1.0.0b251001` | `1.8.1` (GA) |
| Azure 통합 패키지 | `agent-framework-azure-ai` (`AzureAIAgentClient`) | `agent-framework-foundry` (`FoundryChatClient`) |
| Python 요구 버전 | `>=3.10` | `>=3.10` (유지) |

> 참고: GA의 `agent-framework` 메타 패키지는 `agent-framework-core[all]`(모든 선택적
> 커넥터)을 끌어오며, 이 중 `agent-framework-azure-ai-search`가 해석 불가능한
> pre-release 의존성(`azure-search-documents`)을 요구해 잠금 파일 생성이 실패합니다.
> 본 데모는 `agent_framework`(= `agent-framework-core`)와 `agent_framework.foundry`
> (= `agent-framework-foundry`)만 사용하므로, 무거운 메타 패키지 대신 실제로 필요한
> 두 패키지에만 직접 의존하도록 정리했습니다.

---

## 2. 마이그레이션 방법

1. **현재 버전 식별**: `pyproject.toml`과 `uv.lock`에서 베타 버전(`1.0.0b251001`)을 확인.
2. **최신 GA 확인**: PyPI에서 `agent-framework` / `agent-framework-core`의 최신 GA가
   `1.8.1`임을 확인. Azure 패키지가 `agent-framework-azure-ai`에서
   `agent-framework-foundry`로 재구성된 것을 확인.
3. **GA API 분석**: 격리된 가상환경에 GA 패키지를 설치하고 실제 클래스/시그니처를
   리버스 엔지니어링하여 베타→GA의 주요 파괴적 변경 사항을 도출.
4. **소스 코드 마이그레이션**: `core/` 모듈 전반에 외과적(surgical) 수정을 적용.
5. **검증**: 린트(ruff), 임포트/빌드 검증, 그리고 가짜(fake) 채팅 클라이언트를 이용한
   **오프라인 엔드-투-엔드 테스트**(승인/거부 두 경로 모두)로 동작을 확인.
6. **문서/잠금 파일 갱신**: `README.md`의 코드 예시를 GA API로 갱신하고 `uv.lock` 재생성.

> Azure 자격 증명/네트워크가 없는 샌드박스 환경이므로 실제 LLM 호출 대신, GA의
> `BaseChatClient`를 상속한 가짜 클라이언트로 워크플로우 전체 경로를 구동하여 검증했습니다.

---

## 3. 주요 파괴적 변경 사항 및 대응

| 영역 | 베타 (이전) | GA 1.8.1 (이후) |
| --- | --- | --- |
| 에이전트 생성 | `chat_client.create_agent(instructions=, name=)` | `Agent(client=chat_client, instructions=, name=)` |
| 동시 실행 빌더 | `ConcurrentBuilder().participants([...]).build()` | `ConcurrentBuilder(participants=[...]).build()` |
| `ConcurrentBuilder` 위치 | `agent_framework` | `agent_framework.orchestrations` |
| 워크플로우 빌더 시작 노드 | `WorkflowBuilder().set_start_executor(x)` | `WorkflowBuilder(start_executor=x)` |
| 에이전트 응답 접근 | `response.agent_run_response` | `response.agent_response` |
| 실행 API | `workflow.run_stream(x)` | `workflow.run(x, stream=True)` |
| 응답 재개(HIL) | `send_responses_streaming(p)` | `workflow.run(stream=True, responses=p)` |
| 이벤트 타입 | `WorkflowOutputEvent` / `WorkflowStatusEvent` / `RequestInfoEvent` 클래스 | 단일 `WorkflowEvent` + `event.type` 문자열(`"output"`, `"status"`, `"failed"`, `"request_info"` 등) |
| Human-in-the-Loop | `RequestInfoExecutor` / `RequestInfoMessage` / `RequestResponse` 노드 | 실행기 내부에서 `await ctx.request_info(...)` 호출 + `@response_handler` |
| Azure 클라이언트 | `AzureAIAgentClient(model_deployment_name=, async_credential=)` | `FoundryChatClient(model=, credential=)` (`agent_framework.foundry`) |

### Human-in-the-Loop 모델 변경 (가장 큰 개념적 변화)

- 베타에서는 별도의 `RequestInfoExecutor` 노드와
  `approval_manager ↔ human_approver` 간 양방향 엣지로 사람 승인을 처리했습니다.
- GA에서는 승인 실행기 내부에서 `await ctx.request_info(request_data=..., response_type=str)`
  를 호출하면 워크플로우가 일시 중지되고 `request_info` 이벤트가 방출됩니다. 사람의
  응답은 `@response_handler`로 표시된 메서드가 처리하며, 데코레이터는 인자 타입
  주석으로부터 요청/응답 타입을 추론합니다(따라서 타입 주석이 필수).
- 이에 따라 워크플로우 그래프에서 `human_approver` 노드와 양방향 엣지가 제거되었습니다.

### 실행 상태(WorkflowRunState) 처리

- 보류 중인 요청이 있을 때 상태는 `IDLE`이 아니라 `IDLE_WITH_PENDING_REQUESTS`입니다.
  따라서 메인 루프는 순수 `IDLE`/`FAILED`일 때만 종료하고, 보류 요청이 있는 동안에는
  계속해서 사람 응답을 처리하도록 했습니다.

---

## 4. 파일별 변경 내역

- **`pyproject.toml`**
  - 의존성을 GA로 교체: `agent-framework-core==1.8.1`, `agent-framework-foundry==1.8.1`.
  - 무거운 `agent-framework` 메타 패키지 및 더 이상 존재하지 않는 `[viz]` extra 제거.
  - `agent-framework-foundry`가 pre-release(`azure-ai-inference`)를 고정하므로
    `[tool.uv]`에 `prerelease = "allow"`를 추가하여 잠금 파일 해석이 가능하도록 함.

- **`core/agents.py`**
  - 임포트를 `from agent_framework import (Agent, AgentExecutor)` 및
    `from agent_framework.orchestrations import ConcurrentBuilder`로 변경.
  - 5개 에이전트 생성부를 `Agent(client=...)` 패턴으로 변경.
  - `ConcurrentBuilder(participants=[...]).build()`로 변경.

- **`core/approval.py`**
  - `RequestInfoMessage`/`RequestInfoExecutor`/`RequestResponse` 의존 제거,
    `response_handler` 도입.
  - `ClothingConceptApprovalRequest`를 일반 `@dataclass`로 변경.
  - `start_approval`이 `await ctx.request_info(request_data=..., response_type=str)`를 호출.
  - `route_decision`을 `@response_handler`(`original_request`, `feedback`, `ctx` 시그니처)로 전환.
  - 더 이상 사용하지 않는 `create_zava_human_approver()`는 비활성화(`None` 반환).

- **`core/executors.py`**
  - 미사용 임포트 정리.
  - 에이전트 응답 접근을 `.agent_run_response` → `.agent_response`로 변경.

- **`core/workflow_manager.py`**
  - 채팅 클라이언트 초기화를 `FoundryChatClient`(`agent_framework.foundry`)로 변경
    (`model=`, `credential=`).
  - 워크플로우 빌드: `WorkflowBuilder(start_executor=...)`, `human_approver` 노드/엣지 제거.
  - 실행 루프: `run(x, stream=True)` 및 `run(stream=True, responses=p)` 사용.
  - 이벤트 처리: `event.type` 문자열 기반으로 통일.
  - `_track_workflow_progress`: `source_executor_id`는 `request_info` 이벤트에서만 접근하도록
    수정(GA에서 해당 프로퍼티는 다른 이벤트 타입에서 접근 시 `RuntimeError`를 던짐).
  - 기존 코드에 섞여 있던 한글 자모 오타(`handle_approved_concㅇept`) 수정.

- **`README.md`**
  - 코드 예시를 GA API로 갱신(`FoundryChatClient`, `Agent(client=...)`,
    `ConcurrentBuilder(participants=...)`, `WorkflowBuilder(start_executor=...)`,
    `ctx.request_info` 기반 HIL). 아키텍처 다이어그램에서 `zava_human_approver` 노드 제거.

- **`uv.lock`**
  - GA 의존성으로 재생성. 베타(`1.0.0b251001`) 및 `agent-framework-azure-ai` 참조 제거.

---

## 5. 테스트 및 결과

### 검증 항목

| 검증 | 방법 | 결과 |
| --- | --- | --- |
| 모듈 임포트 | GA 환경에서 `core` 전 모듈 임포트 | ✅ 통과 |
| Foundry 클라이언트 임포트 | `agent_framework.foundry.FoundryChatClient` | ✅ 통과 |
| 워크플로우 빌드 | 가짜 채팅 클라이언트로 그래프 구성 | ✅ 통과 |
| 엔드-투-엔드 (승인) | 샘플 PPTX 입력 → 전체 파이프라인 → "yes" 승인 | ✅ `APPROVED` |
| 엔드-투-엔드 (거부) | 동일 파이프라인 → "no" 거부 | ✅ `REJECTED` |
| 린트(ruff) | 마이그레이션 대상 파일 | ✅ 신규 오류 없음 (대상 파일 오류 43→8, 잔여는 모두 기존 이슈) |
| 잠금 파일 | `uv lock` 재생성 | ✅ 베타/azure-ai 참조 0건 |

### 엔드-투-엔드 테스트 상세

Azure 자격 증명이 없는 환경이므로 GA의 `BaseChatClient`를 상속한 가짜 클라이언트로
LLM 호출을 대체하고, 다음 전체 경로를 두 시나리오(승인/거부)에 대해 구동했습니다.

```
PPTX 파싱 → 입력 적응 → 분석 프롬프트 추출 → 동시 분석(4개 에이전트)
  → 분석 결과 로깅 → 리포트 작성 에이전트 → 승인 요청 변환
  → ctx.request_info (사람 승인 일시 중지) → 사람 결정
  → 조건부 라우팅(승인/거부) → 최종 핸들러 → 출력
```

- 승인 경로: 최종 출력 `APPROVED` (예상값 일치)
- 거부 경로: 최종 출력 `REJECTED` (예상값 일치)
- 종료 코드 0으로 두 시나리오 모두 통과

> 잔여 ruff 경고(B904, 미사용 `tracer`/`svg_file`, 프롬프트 문자열 내 공백)는 모두
> 마이그레이션과 무관한 기존 이슈이며, 변경 범위를 최소화하기 위해 손대지 않았습니다.

---

## 6. 남은 사항 / 참고

- **실서비스 검증**: 실제 Azure AI Foundry 엔드포인트와 모델 배포가 있는 환경에서는
  `az login` 후 `AZURE_AI_PROJECT_ENDPOINT`, `AZURE_AI_MODEL_DEPLOYMENT_NAME`를
  설정하여 실제 LLM 기반 엔드-투-엔드 동작을 추가로 확인하는 것을 권장합니다.
- **시각화 extra**: GA에서 `[viz]` extra가 사라졌습니다. `WorkflowViz`의 SVG 내보내기는
  graphviz가 필요하지만 해당 코드는 try/except로 감싸져 있어 graphviz가 없어도
  Mermaid 출력으로 정상 동작합니다.
