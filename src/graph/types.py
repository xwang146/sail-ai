# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from langgraph.graph import MessagesState

from src.prompts.planner_model import Plan
from src.rag import Resource


# declare a list of common questions that will be asked to the user to clarify the research topic
CLARIFY_QUESTIONS = [
    # "您的首选出海国家是什么？",
    "您的计划出海方式是什么？ (例：找代理, 开网店, 开实体店)",
    # "您的主打出海产品是什么？ (列出1-3款)",
    "您的目标客户群体是什么？ (例：当地人, 华人, 年轻人)",
    "您的计划出海预算是什么？ (输入数字，单位：万元)",
]

class State(MessagesState):
    """State for the agent system, extends MessagesState with next field."""

    # Runtime Variables
    locale: str = "en-US"
    answers_to_clarify_questions: list[str] = []
    research_topic: str = ""
    observations: list[str] = []
    resources: list[Resource] = []
    plan_iterations: int = 0
    current_plan: Plan | str = None
    final_report: str = ""
    auto_accepted_plan: bool = False
    enable_background_investigation: bool = True
    background_investigation_results: str = None
