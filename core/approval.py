"""
Human approval workflow components for Zava clothing concept evaluation.

This module handles the human-in-the-loop approval process where Zava team members
review and make final decisions on clothing concept submissions.
"""

from typing import Any
from dataclasses import dataclass

from agent_framework import (
    Executor,
    WorkflowContext,
    RequestInfoMessage,
    RequestInfoExecutor,
    RequestResponse,
    handler
)


@dataclass
class ClothingConceptApprovalRequest(RequestInfoMessage):
    """
    Data structure for requesting human approval of clothing concepts.

    This class extends RequestInfoMessage to provide structured approval
    requests for Zava's clothing concept evaluation workflow.
    """

    question: str = "Do you approve this clothing concept? (yes/no)"
    context: str = ""
    analysis_content: str = ""  # Store the analysis content in the request

    def __str__(self) -> str:
        """Return a formatted string representation of the approval request."""
        return f"""
ZAVA CLOTHING CONCEPT APPROVAL REQUEST

{self.question}

CONCEPT ANALYSIS CONTEXT:
{self.context}

Please review the above analysis and decide whether to approve this clothing
concept for development or reject it for reconsideration.

Response Options:
- Type 'yes' to APPROVE the concept for development
- Type 'no' to REJECT the concept

Your decision will determine the next steps in our evaluation process.
        """.strip()


@dataclass
class ZavaApprovalDecision:
    """
    Data structure to represent approval decisions for clothing concepts.

    This class encapsulates the decision outcome and associated metadata
    for tracking approval workflow results.
    """

    approved: bool
    feedback: str = ""
    analysis_content: str = ""  # Store the analysis content for saving

    def __str__(self) -> str:
        """Return a formatted string representation of the decision."""
        status = "APPROVED" if self.approved else "REJECTED"
        return f"Decision: {status}" + (f" - {self.feedback}" if self.feedback else "")


class ZavaConceptApprovalManager(Executor):
    """
    Manages the human approval workflow for clothing concept evaluation.

    This executor handles the routing of approval requests and processes
    the human decisions to determine next steps in the workflow.
    """

    def __init__(self, id: str = "zava_approval_manager"):
        super().__init__(id=id)

    @handler
    async def start_approval(self, analysis_results: Any, ctx: WorkflowContext[ClothingConceptApprovalRequest]) -> None:
        """Initiates approval request to human."""
        print("=" * 80)
        print("APPROVAL MANAGER: start_approval handler called")
        print("=" * 80)
        print(f"APPROVAL MANAGER: Received analysis_results type: {type(analysis_results)}")
        print(f"APPROVAL MANAGER: Analysis results length: {len(str(analysis_results))} chars")
        print("Starting Zava concept approval process...")

        # Extract key information from analysis results
        analysis_text = str(analysis_results) if analysis_results else "No analysis provided"

        print("=" * 60)
        print("FASHION ANALYSIS RESULTS:")
        print("=" * 60)
        print(analysis_text[:1000] + ('...' if len(analysis_text) > 1000 else ''))
        print("=" * 60)

        # Create comprehensive context for the approval decision
        approval_context = f"""
    종합 의류 컨셉 분석 요약

    패션 분석 에이전트들이 이 의류 컨셉 제출에 대한 평가를 완료했습니다.
    아래는 시장 잠재력, 디자인 장점, 생산 가능성을 다루는 통합 분석입니다:

    {analysis_text}

    주요 결정 요소:
    • 현재 패션 트렌드와의 시장 적합성
    • 디자인 혁신성 및 Zava 브랜드 적합성
    • 생산 가능성 및 비용 고려사항
    • 경쟁 차별화 잠재력
    • 회사 목표와의 전략적 일치성

    이 결정은 Zava가 컨셉 개발을 진행할지, 아니면 향후 제출을 위한
    건설적인 피드백을 제공할지를 결정합니다.
        """.strip()

        approval_request = ClothingConceptApprovalRequest(
            question="위의 종합 패션 분석을 바탕으로, Zava가 이 의류 컨셉을 개발 승인해야 할까요?",
            context=approval_context,
            analysis_content=analysis_text
        )

        print("APPROVAL MANAGER: Sending approval request to Zava design team...")
        print(f"APPROVAL MANAGER: Approval request type: {type(approval_request)}")
        print(f"APPROVAL MANAGER: Request question: {approval_request.question[:50]}...")
        await ctx.send_message(approval_request)
        print("APPROVAL MANAGER: Approval request sent successfully to human approver")
        print("=" * 80)

    @handler
    async def route_decision(
        self,
        response: RequestResponse[ClothingConceptApprovalRequest, str],
        ctx: WorkflowContext[ZavaApprovalDecision]
    ) -> None:
        """Processes human response and prepares routing decision."""
        print("=" * 80)
        print("APPROVAL MANAGER: route_decision handler called")
        print("=" * 80)
        print(f"APPROVAL MANAGER: Received response type: {type(response)}")
        print(f"APPROVAL MANAGER: Response data: {response.data}")

        if hasattr(response, 'original_request'):
            print(f"APPROVAL MANAGER: Original request type: {type(response.original_request)}")
            print(f"APPROVAL MANAGER: Original request question: {response.original_request.question[:50]}..." if hasattr(response.original_request, 'question') else "N/A")

        print("Processing human approval response...")
        human_input = (response.data or "").strip().lower()
        print(f"APPROVAL MANAGER: Human input normalized: '{human_input}'")

        # Parse human input into routing decision
        approved = human_input in ["yes", "y", "approve", "approved"]
        print(f"APPROVAL MANAGER: Approval status: {approved}")

        # Get analysis content from the original request
        analysis_content = response.original_request.analysis_content if response.original_request else ""
        print(f"APPROVAL MANAGER: Analysis content length: {len(analysis_content)} chars")

        decision = ZavaApprovalDecision(
            approved=approved,
            feedback=response.data or "",
            analysis_content=analysis_content
        )
        print(f"APPROVAL MANAGER: Created decision: {decision}")

        print(f"Zava team decision - {'APPROVED' if approved else 'REJECTED'}")
        print("APPROVAL MANAGER: Sending decision to trigger conditional routing...")
        await ctx.send_message(decision)
        print("APPROVAL MANAGER: Decision sent successfully")
        print("=" * 80)


def concept_approval_condition(decision: Any) -> bool:
    """
    Condition function to check if a clothing concept was approved.

    Args:
        decision: Human approval response (RequestResponse or str)

    Returns:
        True if the concept was approved, False otherwise
    """
    print("=" * 60)
    print("CONDITION: concept_approval_condition called")
    print(f"CONDITION: Decision type: {type(decision)}")
    print(f"CONDITION: Decision value: {decision}")

    # Handle RequestResponse from human approver
    if hasattr(decision, 'data'):
        print(f"CONDITION: Has data attribute, data type: {type(decision.data)}")
        print(f"CONDITION: Data value: {decision.data}")

        # Handle nested RequestResponse
        if hasattr(decision.data, 'data'):
            print("CONDITION: Detected nested RequestResponse - extracting inner data")
            response_text = str(decision.data.data).lower().strip()
        else:
            response_text = str(decision.data).lower().strip()

        result = response_text in ['yes', 'y', 'approve', 'approved']
        print(f"CONDITION: Approval check result: {result} (response_text: '{response_text}')")
        print("=" * 60)
        return result

    # Handle string responses directly
    if isinstance(decision, str):
        result = decision.lower().strip() in ['yes', 'y', 'approve', 'approved']
        print(f"CONDITION: String approval check result: {result} (decision: '{decision}')")
        print("=" * 60)
        return result

    # Handle ZavaApprovalDecision objects
    if isinstance(decision, ZavaApprovalDecision):
        result = decision.approved
        print(f"CONDITION: ZavaApprovalDecision approval result: {result}")
        print(f"CONDITION: Decision details - approved: {decision.approved}, feedback: '{decision.feedback}'")
        print("=" * 60)
        return result

    # Handle ClothingConceptApprovalRequest (should be ignored in conditions)
    if isinstance(decision, ClothingConceptApprovalRequest):
        print("CONDITION: Received ClothingConceptApprovalRequest - ignoring (not a response)")
        print("=" * 60)
        return False

    # Handle other types by checking for approval attributes
    if hasattr(decision, 'approved'):
        result = decision.approved
        print(f"CONDITION: Approved attribute result: {result}")
        print("=" * 60)
        return result

    # Default to False for unknown types
    print("CONDITION: Unknown type - defaulting to False")
    print("=" * 60)
    return False


def concept_rejection_condition(decision: Any) -> bool:
    """
    Condition function to check if a clothing concept was rejected.

    Args:
        decision: Human approval response (RequestResponse or str)

    Returns:
        True if the concept was rejected, False otherwise
    """
    print("=" * 60)
    print("CONDITION: concept_rejection_condition called")
    print(f"CONDITION: Decision type: {type(decision)}")
    print(f"CONDITION: Decision value: {decision}")

    # Handle RequestResponse from human approver
    if hasattr(decision, 'data'):
        print(f"CONDITION: Has data attribute, data type: {type(decision.data)}")
        print(f"CONDITION: Data value: {decision.data}")

        # Handle nested RequestResponse
        if hasattr(decision.data, 'data'):
            print("CONDITION: Detected nested RequestResponse - extracting inner data")
            response_text = str(decision.data.data).lower().strip()
        else:
            response_text = str(decision.data).lower().strip()

        result = response_text in ['no', 'n', 'reject', 'rejected', 'deny', 'denied']
        print(f"CONDITION: Rejection check result: {result} (response_text: '{response_text}')")
        print("=" * 60)
        return result

    # Handle string responses directly
    if isinstance(decision, str):
        result = decision.lower().strip() in ['no', 'n', 'reject', 'rejected', 'deny', 'denied']
        print(f"CONDITION: String rejection check result: {result} (decision: '{decision}')")
        print("=" * 60)
        return result

    # Handle ZavaApprovalDecision objects
    if isinstance(decision, ZavaApprovalDecision):
        result = not decision.approved
        print(f"CONDITION: ZavaApprovalDecision rejection result: {result}")
        print(f"CONDITION: Decision details - approved: {decision.approved}, feedback: '{decision.feedback}'")
        print("=" * 60)
        return result

    # Handle ClothingConceptApprovalRequest (should be ignored in conditions)
    if isinstance(decision, ClothingConceptApprovalRequest):
        print("CONDITION: Received ClothingConceptApprovalRequest - ignoring (not a response)")
        print("=" * 60)
        return False

    # Handle other types by checking for approval attributes
    if hasattr(decision, 'approved'):
        result = not decision.approved
        print(f"CONDITION: Approved attribute rejection result: {result}")
        print("=" * 60)
        return result

    # Default to True (reject) for unknown types as a safety measure
    print("CONDITION: Unknown type - defaulting to True (reject)")
    print("=" * 60)
    return True


def create_zava_human_approver() -> RequestInfoExecutor:
    """
    Create a human approver executor for Zava clothing concept decisions.

    Returns:
        RequestInfoExecutor configured for human approval workflow
    """
    return RequestInfoExecutor(id="zava_human_approver")


# Convenience aliases for backward compatibility and clarity
yes_condition = concept_approval_condition
no_condition = concept_rejection_condition