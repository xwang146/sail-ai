# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import logging
import os
from typing import Annotated, Literal

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.types import Command, interrupt
from langchain_mcp_adapters.client import MultiServerMCPClient

from src.agents import create_agent
from src.tools.search import LoggedTavilySearch
from src.tools import (
    crawl_tool,
    get_web_search_tool,
    get_retriever_tool,
    python_repl_tool,
)

from src.config.agents import AGENT_LLM_MAP
from src.config.configuration import Configuration
from src.llms.llm import get_llm_by_type
from src.prompts.planner_model import Plan
from src.prompts.template import apply_prompt_template
from src.utils.json_utils import repair_json_output
from src.utils.context_manager import truncate_observations, truncate_step_findings, check_context_length

from .types import State, CLARIFY_QUESTIONS
from ..config import SELECTED_SEARCH_ENGINE, SearchEngine

logger = logging.getLogger(__name__)


@tool
def handoff_to_planner(
    research_topic: Annotated[str, "The topic of the research task to be handed off."],
    locale: Annotated[str, "The user's detected language locale (e.g., en-US, zh-CN)."],
):
    """Handoff to planner agent to do plan."""
    # This tool is not returning anything: we're just using it
    # as a way for LLM to signal that it needs to hand off to planner agent
    return

@tool
def handoff_to_coordinator(
    research_topic: Annotated[str, "The topic of the research task to be handed off."],
    locale: Annotated[str, "The user's detected language locale (e.g., en-US, zh-CN)."],
):
    """Handoff to coordinator agent to do plan."""
    # This tool is not returning anything: we're just using it
    # as a way for LLM to signal that it needs to hand off to coordinator agent
    return


def background_investigation_node(state: State, config: RunnableConfig):
    logger.info("background investigation node is running.")
    configurable = Configuration.from_runnable_config(config)
    query = state.get("research_topic")
    background_investigation_results = None
    if SELECTED_SEARCH_ENGINE == SearchEngine.TAVILY.value:
        searched_content = LoggedTavilySearch(
            max_results=configurable.max_search_results
        ).invoke(query)
        if isinstance(searched_content, list):
            background_investigation_results = [
                f"## {elem['title']}\n\n{elem['content']}" for elem in searched_content
            ]
            return {
                "background_investigation_results": "\n\n".join(
                    background_investigation_results
                )
            }
        else:
            logger.error(
                f"Tavily search returned malformed response: {searched_content}"
            )
    else:
        background_investigation_results = get_web_search_tool(
            configurable.max_search_results, include_images=False
        ).invoke(query)
    return {
        "background_investigation_results": json.dumps(
            background_investigation_results, ensure_ascii=False
        )
    }


def planner_node(
    state: State, config: RunnableConfig
) -> Command[Literal["human_feedback", "reporter"]]:
    """Planner node that generate the full plan."""
    logger.info("********** [PlannerNode] 开始生成完整计划")
    logger.info(f"[PlannerNode] 当前状态: plan_iterations={state.get('plan_iterations', 0)}, locale={state.get('locale', 'en-US')}")
    logger.info(f"[PlannerNode] 用户消息数量: {len(state.get('messages', []))}")
    
    # 打印用户消息内容
    for i, msg in enumerate(state.get('messages', [])):
        if isinstance(msg, dict):
            logger.info(f"[PlannerNode] 消息 {i+1}: role={msg.get('role', 'unknown')}, content={msg.get('content', '')[:100]}...")
        else:
            logger.info(f"[PlannerNode] 消息 {i+1}: type={type(msg)}, content={getattr(msg, 'content', '')[:100] if hasattr(msg, 'content') else 'N/A'}...")
    
    configurable = Configuration.from_runnable_config(config)
    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    logger.info(f"[PlannerNode] 配置信息: max_plan_iterations={configurable.max_plan_iterations}, enable_deep_thinking={configurable.enable_deep_thinking}")
    
    logger.info("[PlannerNode] 步骤1: 应用 planner 模板")
    messages = apply_prompt_template("planner", state, configurable)
    logger.info(f"[PlannerNode] 应用模板后的消息数量: {len(messages)}")
    
    # 打印模板消息内容
    for i, msg in enumerate(messages):
        if isinstance(msg, dict):
            logger.info(f"[PlannerNode] 模板消息 {i+1}: role={msg.get('role', 'unknown')}, content={msg.get('content', '')[:100]}...")
        else:
            logger.info(f"[PlannerNode] 模板消息 {i+1}: type={type(msg)}")

    logger.info("[PlannerNode] 步骤2: 检查背景调查结果")
    if state.get("enable_background_investigation") and state.get(
        "background_investigation_results"
    ):
        logger.info(f"[PlannerNode] 添加背景调查结果，长度: {len(state['background_investigation_results'])}")
        logger.info(f"[PlannerNode] 背景调查内容: {state['background_investigation_results'][:200]}...")
        messages += [
            {
                "role": "user",
                "content": (
                    "background investigation results of user query:\n"
                    + state["background_investigation_results"]
                    + "\n"
                ),
            }
        ]
    else:
        logger.info("[PlannerNode] 没有背景调查结果或未启用背景调查")

    logger.info("[PlannerNode] 步骤3: 选择 LLM 模型")
    if configurable.enable_deep_thinking:
        llm = get_llm_by_type("reasoning")
        logger.info("[PlannerNode] 使用 reasoning LLM")
    elif AGENT_LLM_MAP["planner"] == "basic":
        llm = get_llm_by_type("basic").with_structured_output(
            Plan,
            method="json_mode",
        )
        logger.info("[PlannerNode] 使用 basic LLM with structured output")
    else:
        llm = get_llm_by_type(AGENT_LLM_MAP["planner"])
        logger.info(f"[PlannerNode] 使用 {AGENT_LLM_MAP['planner']} LLM")

    logger.info("[PlannerNode] 步骤4: 检查计划迭代次数")
    # if the plan iterations is greater than the max plan iterations, return the reporter node
    if plan_iterations >= configurable.max_plan_iterations:
        logger.info(f"[PlannerNode] 计划迭代次数已达上限 ({plan_iterations}/{configurable.max_plan_iterations})，跳转到 reporter")
        return Command(goto="reporter")

    logger.info("[PlannerNode] 步骤5: 调用 LLM 生成计划")
    full_response = ""
    if AGENT_LLM_MAP["planner"] == "basic" and not configurable.enable_deep_thinking:
        logger.info("[PlannerNode] 调用 LLM (basic mode)")
        response = llm.invoke(messages)
        full_response = response.model_dump_json(indent=4, exclude_none=True)
    else:
        logger.info("[PlannerNode] 调用 LLM (stream mode)")
        response = llm.stream(messages)
        for chunk in response:
            full_response += chunk.content
    
    logger.info(f"[PlannerNode] LLM 响应长度: {len(full_response)}")
    logger.info(f"[PlannerNode] LLM 响应内容: {full_response}")

    logger.info("[PlannerNode] 步骤6: 解析 JSON 响应")
    try:
        curr_plan = json.loads(repair_json_output(full_response))
        logger.info(f"[PlannerNode] JSON 解析成功，计划标题: {curr_plan.get('title', 'N/A')}")
        logger.info(f"[PlannerNode] 计划步骤数量: {len(curr_plan.get('steps', []))}")
        logger.info(f"[PlannerNode] has_enough_context: {curr_plan.get('has_enough_context', False)}")
        
        # 打印计划步骤详情
        for i, step in enumerate(curr_plan.get('steps', [])):
            logger.info(f"[PlannerNode] 步骤 {i+1}: title={step.get('title', 'N/A')}, description={step.get('description', 'N/A')[:100]}...")
            
    except json.JSONDecodeError:
        logger.warning("[PlannerNode] LLM 响应不是有效的 JSON")
        if plan_iterations > 0:
            logger.info("[PlannerNode] 计划迭代次数 > 0，跳转到 reporter")
            return Command(goto="reporter")
        else:
            logger.info("[PlannerNode] 计划迭代次数 = 0，结束工作流")
            return Command(goto="__end__")
    
    logger.info("[PlannerNode] 步骤7: 检查上下文是否足够")
    if curr_plan.get("has_enough_context"):
        logger.info("[PlannerNode] 计划有足够上下文，跳转到 reporter")
        new_plan = Plan.model_validate(curr_plan)
        return Command(
            update={
                "messages": [AIMessage(content=full_response, name="planner")],
                "current_plan": new_plan,
            },
            goto="reporter",
        )
    
    logger.info("[PlannerNode] 计划需要更多上下文，跳转到 human_feedback")
    return Command(
        update={
            "messages": [AIMessage(content=full_response, name="planner")],
            "current_plan": full_response,
        },
        goto="human_feedback",
    )


def human_feedback_node(
    state,
) -> Command[Literal["planner", "research_team", "reporter", "__end__"]]:
    current_plan = state.get("current_plan", "")
    # check if the plan is auto accepted
    auto_accepted_plan = state.get("auto_accepted_plan", False)
    if not auto_accepted_plan:
        feedback = interrupt("Please Review the Plan.")

        # if the feedback is not accepted, return the planner node
        if feedback and str(feedback).upper().startswith("[EDIT_PLAN]"):
            return Command(
                update={
                    "messages": [
                        HumanMessage(content=feedback, name="feedback"),
                    ],
                },
                goto="planner",
            )
        elif feedback and str(feedback).upper().startswith("[ACCEPTED]"):
            logger.info("Plan is accepted by user.")
        else:
            raise TypeError(f"Interrupt value of {feedback} is not supported.")

    # if the plan is accepted, run the following node
    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    goto = "research_team"
    try:
        current_plan = repair_json_output(current_plan)
        # increment the plan iterations
        plan_iterations += 1
        # parse the plan
        new_plan = json.loads(current_plan)
        if new_plan["has_enough_context"]:
            goto = "reporter"
    except json.JSONDecodeError:
        logger.warning("Planner response is not a valid JSON")
        if plan_iterations > 1:  # the plan_iterations is increased before this check
            return Command(goto="reporter")
        else:
            return Command(goto="__end__")

    return Command(
        update={
            "current_plan": Plan.model_validate(new_plan),
            "plan_iterations": plan_iterations,
            "locale": new_plan["locale"],
        },
        goto=goto,
    )


def questioner_node(state: State, config: RunnableConfig) -> Command[Literal["coordinator", "__end__"]] | dict:
    """依次向用户提问澄清问题，收集答案，全部完成后跳转到 coordinator。"""
    logger.info("questioner_node 正在运行。当前 state.answers_to_clarify_questions: %s", state.get("answers_to_clarify_questions", []))
    
    configurable = Configuration.from_runnable_config(config)
    messages = apply_prompt_template("questioner", state)

    answers = state.get("answers_to_clarify_questions", [])
    next_idx = len(answers)

    llm = get_llm_by_type("basic")
    
    # 如果所有问题都已完成，跳转到 coordinator
    if next_idx >= len(CLARIFY_QUESTIONS):
        logger.info("所有澄清问题已完成，跳转到 coordinator")
        
        completion_response = llm.invoke(messages + [
            HumanMessage(content="All clarifying questions have been answered. Please provide a compliment and hand off to coordinator.")
        ])
        
        return Command(
            update={
                "messages": [AIMessage(content=completion_response.content, name="questioner")],
                "answers_to_clarify_questions": answers
            },
            goto="coordinator"
        )
    
    # 处理当前需要回答的问题
    question = CLARIFY_QUESTIONS[next_idx]
    logger.info(f"当前已回答 {next_idx} 个问题，总共 {len(CLARIFY_QUESTIONS)} 个问题。")
    logger.info(f"即将提问第 {next_idx+1} 个问题: {question}")
    
    # 生成包含赞美的提问
    prompt = f"""
            现在向用户提出这个问题：{question}
            """
    
    logger.info(f"questioner_node 调用 LLM 生成友好提问: {prompt}")
    response = llm.invoke(messages + [HumanMessage(content=prompt)])

    friendly_question = response.content
    logger.info(f"生成的友好提问: {friendly_question}")

    answers.append("new_answer"+str(next_idx))
    
    return {
        "messages": [AIMessage(content=friendly_question, name="questioner")],
        "answers_to_clarify_questions": answers
    }
    

def coordinator_node(
    state: State, config: RunnableConfig
) -> Command[Literal["planner", "background_investigator", "__end__"]]:
    """Coordinator node that communicate with customers."""
    logger.info("Coordinator talking.")
    configurable = Configuration.from_runnable_config(config)
    messages = apply_prompt_template("coordinator", state)
    response = (
        get_llm_by_type(AGENT_LLM_MAP["coordinator"])
        .bind_tools([handoff_to_planner])
        .invoke(messages)
    )
    logger.debug(f"Current state messages: {state['messages']}")

    goto = "__end__"
    locale = state.get("locale", "zh-CN")  # Default locale if not specified
    research_topic = state.get("research_topic", "")

    if len(response.tool_calls) > 0:
        goto = "planner"
        if state.get("enable_background_investigation"):
            # if the search_before_planning is True, add the web search tool to the planner agent
            goto = "background_investigator"
        try:
            for tool_call in response.tool_calls:
                if tool_call.get("name", "") != "handoff_to_planner":
                    continue
                if tool_call.get("args", {}).get("locale") and tool_call.get(
                    "args", {}
                ).get("research_topic"):
                    locale = tool_call.get("args", {}).get("locale")
                    research_topic = tool_call.get("args", {}).get("research_topic")
                    break
        except Exception as e:
            logger.error(f"Error processing tool calls: {e}")
    else:
        logger.warning(
            "Coordinator response contains no tool calls. Terminating workflow execution."
        )
        logger.debug(f"Coordinator response: {response}")

    logger.info(f"coordinator_node 响应内容: {response.content}")
    logger.info(f"coordinator_node 返回 Command，goto: {goto}，update: {{'locale': {locale}, 'research_topic': {research_topic}, 'resources': {configurable.resources}}}")

    return Command(
        update={
            "locale": locale,
            "research_topic": research_topic,
            "resources": configurable.resources,
        },
        goto=goto,
    )


def reporter_node(state: State, config: RunnableConfig):
    """Reporter node that write a final report."""
    logger.info("Reporter write final report")
    configurable = Configuration.from_runnable_config(config)
    current_plan = state.get("current_plan")
    input_ = {
        "messages": [
            HumanMessage(
                f"# Research Requirements\n\n## Task\n\n{current_plan.title}\n\n## Description\n\n{current_plan.thought}"
            )
        ],
        "locale": state.get("locale", "zh-CN"),
    }
    invoke_messages = apply_prompt_template("reporter", input_, configurable)
    observations = state.get("observations", [])

    # Add a reminder about the new report format, citation style, and table usage
    invoke_messages.append(
        HumanMessage(
            content="IMPORTANT: Structure your report according to the format in the prompt. Remember to include:\n\n1. Key Points - A bulleted list of the most important findings\n2. Overview - A brief introduction to the topic\n3. Detailed Analysis - Organized into logical sections\n4. Survey Note (optional) - For more comprehensive reports\n5. Key Citations - List all references at the end\n\nFor citations, DO NOT include inline citations in the text. Instead, place all citations in the 'Key Citations' section at the end using the format: `- [Source Title](URL)`. Include an empty line between each citation for better readability.\n\nPRIORITIZE USING MARKDOWN TABLES for data presentation and comparison. Use tables whenever presenting comparative data, statistics, features, or options. Structure tables with clear headers and aligned columns. Example table format:\n\n| Feature | Description | Pros | Cons |\n|---------|-------------|------|------|\n| Feature 1 | Description 1 | Pros 1 | Cons 1 |\n| Feature 2 | Description 2 | Pros 2 | Cons 2 |",
            name="system",
        )
    )

    for observation in observations:
        invoke_messages.append(
            HumanMessage(
                content=f"Below are some observations for the research task:\n\n{observation}",
                name="observation",
            )
        )
    logger.debug(f"Current invoke messages: {invoke_messages}")
    response = get_llm_by_type(AGENT_LLM_MAP["reporter"]).invoke(invoke_messages)
    response_content = response.content
    logger.info(f"reporter_node 响应内容: {response_content}")
    logger.info(f"reporter_node 返回 final_report: {response_content}")

    return {"final_report": response_content}


def research_team_node(state: State):
    """Research team node that collaborates on tasks."""
    logger.info("**********Research team is collaborating on tasks.")
    pass


async def _execute_agent_step(
    state: State, agent, agent_name: str
) -> Command[Literal["research_team"]]:
    """Execute a single agent step."""
    logger.info(f"********** [ExecuteAgentStep] 开始执行 {agent_name} 步骤")
    
    # Get current step and observations
    current_plan = state.get("current_plan")
    if not current_plan:
        logger.error("[ExecuteAgentStep] 没有找到当前计划")
        return Command(goto="research_team")
    
    observations = state.get("observations", [])
    logger.info(f"[ExecuteAgentStep] 当前观察数量: {len(observations)}")
    
    # Find the next step to execute
    completed_steps = [step for step in current_plan.steps if step.execution_res]
    current_step = None
    for step in current_plan.steps:
        if not step.execution_res:
            current_step = step
            break
    
    if not current_step:
        logger.info("[ExecuteAgentStep] 所有步骤已完成，跳转到 research_team")
        return Command(goto="research_team")
    
    logger.info(f"[ExecuteAgentStep] 当前步骤: {current_step.title}")
    logger.info(f"[ExecuteAgentStep] 步骤类型: {current_step.step_type}")
    logger.info(f"[ExecuteAgentStep] 需要搜索: {current_step.need_search}")
    logger.info(f"[ExecuteAgentStep] 当前计划步骤总数: {len(current_plan.steps)}")
    logger.info(f"[ExecuteAgentStep] 已完成步骤数量: {len(completed_steps)}")

    # Format completed steps information with length management
    completed_steps_info = truncate_step_findings(completed_steps, max_findings_length=40000)

    # Prepare the input for the agent with completed steps info
    agent_input = {
        "messages": [
            HumanMessage(
                content=f"{completed_steps_info}# Current Task\n\n## Title\n\n{current_step.title}\n\n## Description\n\n{current_step.description}\n\n## Locale\n\n{state.get('locale', 'en-US')}"
            )
        ]
    }
    logger.info(f"[ExecuteAgentStep] 代理输入消息数量: {len(agent_input['messages'])}")

    # Add citation reminder for researcher agent
    if agent_name == "researcher":
        if state.get("resources"):
            resources_info = "**The user mentioned the following resource files:**\n\n"
            for resource in state.get("resources"):
                resources_info += f"- {resource.title} ({resource.description})\n"
            logger.info(f"[ExecuteAgentStep] 添加资源信息，资源数量: {len(state.get('resources', []))}")

            agent_input["messages"].append(
                HumanMessage(
                    content=resources_info
                    + "\n\n"
                    + "You MUST use the **local_search_tool** to retrieve the information from the resource files.",
                )
            )

        agent_input["messages"].append(
            HumanMessage(
                content="IMPORTANT: DO NOT include inline citations in the text. Instead, track all sources and include a References section at the end using link reference format. Include an empty line between each citation for better readability. Use this format for each reference:\n- [Source Title](URL)\n\n- [Another Source](URL)",
                name="system",
            )
        )

    # Invoke the agent
    default_recursion_limit = 25
    try:
        env_value_str = os.getenv("AGENT_RECURSION_LIMIT", str(default_recursion_limit))
        parsed_limit = int(env_value_str)

        if parsed_limit > 0:
            recursion_limit = parsed_limit
            logger.info(f"[ExecuteAgentStep] 递归限制设置为: {recursion_limit}")
        else:
            logger.warning(
                f"AGENT_RECURSION_LIMIT value '{env_value_str}' (parsed as {parsed_limit}) is not positive. "
                f"Using default value {default_recursion_limit}."
            )
            recursion_limit = default_recursion_limit
    except ValueError:
        raw_env_value = os.getenv("AGENT_RECURSION_LIMIT")
        logger.warning(
            f"Invalid AGENT_RECURSION_LIMIT value: '{raw_env_value}'. "
            f"Using default value {default_recursion_limit}."
        )
        recursion_limit = default_recursion_limit

    logger.info(f"[ExecuteAgentStep] 调用代理: {agent_name}, 递归限制: {recursion_limit}")
    result = await agent.ainvoke(
        input=agent_input, config={"recursion_limit": recursion_limit}
    )

    # Process the result
    response_content = result["messages"][-1].content
    logger.info(f"[ExecuteAgentStep] {agent_name} 响应长度: {len(response_content)}")

    # Update the step with the execution result
    current_step.execution_res = response_content
    logger.info(f"[ExecuteAgentStep] 步骤 '{current_step.title}' 执行完成，由 {agent_name} 执行")

    # 截断观察结果以避免上下文过长
    updated_observations = truncate_observations(observations + [response_content], max_total_length=50000)
    
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=response_content,
                    name=agent_name,
                )
            ],
            "observations": updated_observations,
        },
        goto="research_team",
    )


async def _setup_and_execute_agent_step(
    state: State,
    config: RunnableConfig,
    agent_type: str,
    default_tools: list,
) -> Command[Literal["research_team"]]:
    """Helper function to set up an agent with appropriate tools and execute a step.

    This function handles the common logic for both researcher_node and coder_node:
    1. Configures MCP servers and tools based on agent type
    2. Creates an agent with the appropriate tools or uses the default agent
    3. Executes the agent on the current step

    Args:
        state: The current state
        config: The runnable config
        agent_type: The type of agent ("researcher" or "coder")
        default_tools: The default tools to add to the agent

    Returns:
        Command to update state and go to research_team
    """
    logger.info(f"********** [SetupAgentStep] 开始设置 {agent_type} 代理")
    logger.info(f"[SetupAgentStep] 默认工具数量: {len(default_tools)}")
    
    configurable = Configuration.from_runnable_config(config)
    mcp_servers = {}
    enabled_tools = {}

    # Extract MCP server configuration for this agent type
    if configurable.mcp_settings:
        logger.info(f"[SetupAgentStep] 检查 MCP 服务器配置")
        for server_name, server_config in configurable.mcp_settings["servers"].items():
            if (
                server_config["enabled_tools"]
                and agent_type in server_config["add_to_agents"]
            ):
                mcp_servers[server_name] = {
                    k: v
                    for k, v in server_config.items()
                    if k in ("transport", "command", "args", "url", "env")
                }
                for tool_name in server_config["enabled_tools"]:
                    enabled_tools[tool_name] = server_name
                logger.info(f"[SetupAgentStep] 添加 MCP 服务器: {server_name}, 工具: {server_config['enabled_tools']}")

    # Create and execute agent with MCP tools if available
    if mcp_servers:
        logger.info(f"[SetupAgentStep] 使用 MCP 工具创建代理，服务器数量: {len(mcp_servers)}")
        async with MultiServerMCPClient(mcp_servers) as client:
            loaded_tools = default_tools[:]
            for tool in client.get_tools():
                if tool.name in enabled_tools:
                    tool.description = (
                        f"Powered by '{enabled_tools[tool.name]}'.\n{tool.description}"
                    )
                    loaded_tools.append(tool)
            logger.info(f"[SetupAgentStep] 最终工具数量: {len(loaded_tools)}")
            agent = create_agent(agent_type, agent_type, loaded_tools, agent_type)
            return await _execute_agent_step(state, agent, agent_type)
    else:
        logger.info(f"[SetupAgentStep] 使用默认工具创建代理")
        # Use default tools if no MCP servers are configured
        agent = create_agent(agent_type, agent_type, default_tools, agent_type)
        return await _execute_agent_step(state, agent, agent_type)


async def researcher_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """Researcher node that do research"""
    logger.info("********** [ResearcherNode] 研究员节点开始研究")
    logger.info(f"[ResearcherNode] 当前状态: locale={state.get('locale', 'en-US')}, 资源数量={len(state.get('resources', []))}")
    
    configurable = Configuration.from_runnable_config(config)
    tools = [get_web_search_tool(configurable.max_search_results, include_images=False), crawl_tool]
    retriever_tool = get_retriever_tool(state.get("resources", []))
    if retriever_tool:
        tools.insert(0, retriever_tool)
        logger.info(f"[ResearcherNode] 添加检索工具: {retriever_tool.name}")
    
    logger.info(f"[ResearcherNode] 研究员工具列表: {[tool.name for tool in tools]}")
    logger.info(f"[ResearcherNode] 最大搜索结果数: {configurable.max_search_results}")
    
    return await _setup_and_execute_agent_step(
        state,
        config,
        "researcher",
        tools,
    )


async def coder_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """Coder node that do code analysis."""
    logger.info("Coder node is coding.")
    return await _setup_and_execute_agent_step(
        state,
        config,
        "coder",
        [python_repl_tool],
    )
