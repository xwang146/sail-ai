import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def truncate_observations(observations: List[str], max_total_length: int = 50000) -> List[str]:
    """
    智能截断观察结果列表，保持最重要的信息
    
    Args:
        observations: 观察结果列表
        max_total_length: 最大总长度（字符数）
        
    Returns:
        截断后的观察结果列表
    """
    if not observations:
        return []
    
    # 计算当前总长度
    total_length = sum(len(obs) for obs in observations)
    
    if total_length <= max_total_length:
        return observations
    
    logger.warning(f"观察结果总长度 ({total_length}) 超过限制 ({max_total_length})，开始截断")
    
    # 策略1：保留最新的观察结果（通常更重要）
    truncated_observations = []
    current_length = 0
    
    # 从最新的观察开始，向前添加
    for obs in reversed(observations):
        if current_length + len(obs) <= max_total_length:
            truncated_observations.insert(0, obs)
            current_length += len(obs)
        else:
            # 如果单个观察就超过限制，截断这个观察
            if len(obs) > max_total_length:
                truncated_obs = obs[:max_total_length - current_length - 100] + "\n\n... (内容被截断)"
                truncated_observations.insert(0, truncated_obs)
                current_length += len(truncated_obs)
            break
    
    logger.info(f"截断后保留 {len(truncated_observations)} 个观察结果，总长度: {current_length}")
    
    return truncated_observations


def truncate_step_findings(completed_steps: List[Any], max_findings_length: int = 40000) -> str:
    """
    截断已完成步骤的发现信息
    
    Args:
        completed_steps: 已完成的步骤列表
        max_findings_length: 最大发现信息长度
        
    Returns:
        截断后的发现信息字符串
    """
    if not completed_steps:
        return ""
    
    completed_steps_info = "# Existing Research Findings\n\n"
    total_length = len(completed_steps_info)
    
    for i, step in enumerate(completed_steps):
        step_info = f"## Existing Finding {i + 1}: {step.title}\n\n<finding>\n{step.execution_res}\n</finding>\n\n"
        
        # 检查添加这个步骤是否会超过长度限制
        if total_length + len(step_info) > max_findings_length:
            logger.warning(f"已完成步骤信息过长，截断在第 {i} 个步骤")
            completed_steps_info += f"\n... (还有 {len(completed_steps) - i} 个步骤被截断)\n"
            break
            
        completed_steps_info += step_info
        total_length += len(step_info)
    
    logger.info(f"已完成步骤信息长度: {len(completed_steps_info)}")
    return completed_steps_info


def estimate_token_count(text: str) -> int:
    """
    估算文本的 token 数量（粗略估算）
    
    Args:
        text: 输入文本
        
    Returns:
        估算的 token 数量
    """
    # 简单的估算：英文约4个字符1个token，中文约2个字符1个token
    english_chars = sum(1 for c in text if ord(c) < 128)
    chinese_chars = len(text) - english_chars
    
    estimated_tokens = english_chars // 4 + chinese_chars // 2
    return estimated_tokens


def check_context_length(messages: List[Dict[str, Any]], max_tokens: int = 60000) -> bool:
    """
    检查消息列表的总长度是否超过限制
    
    Args:
        messages: 消息列表
        max_tokens: 最大 token 数量
        
    Returns:
        是否超过限制
    """
    total_text = ""
    for message in messages:
        if isinstance(message, dict):
            total_text += message.get('content', '')
        else:
            total_text += getattr(message, 'content', '')
    
    estimated_tokens = estimate_token_count(total_text)
    logger.info(f"估算的 token 数量: {estimated_tokens}, 限制: {max_tokens}")
    
    return estimated_tokens > max_tokens 