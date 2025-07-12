# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
from langgraph.graph import MessagesState
from langchain_core.messages import SystemMessage

from enum import Enum
from src.prompts.planner_model import Plan
from src.rag import Resource

class ReportType(str, Enum):
    MARKET= "market"
    STRATEGY = "strategy"
    EXECUTION = "execution"
    FINANCE = "finance"
    FINISHED = "finished"


class State(MessagesState):
    """State for the agent system, extends MessagesState with next field."""

    # Runtime Variables
    locale: str = "zh-CN"
    research_topic: str = ""
    observations: list[str] = []
    resources: list[Resource] = []
    plan_iterations: int = 0
    current_plan: Plan | str = None
    final_report: str = ""
    auto_accepted_plan: bool = False
    enable_background_investigation: bool = True
    background_investigation_results: str = None
    # if all reports are done, the workflow will end
    current_report_type: ReportType = ReportType.MARKET
    # company_business: str = ""
    # overseas_area: str = ""
    # last_research_type: ReportType = ReportType.OTHER
