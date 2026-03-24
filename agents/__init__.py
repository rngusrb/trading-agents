import re
import json


def parse_llm_json(text: str) -> dict:
    """
    LLM 응답에서 JSON 추출 (마크다운 코드 블록 처리 포함)

    Args:
        text: LLM raw 응답 텍스트

    Returns:
        dict: 파싱된 JSON 객체
    """
    # ```json ... ``` 또는 ``` ... ``` 블록에서 추출
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    # 코드 블록 없이 바로 JSON이 오는 경우
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError(f"No JSON found in LLM response: {text[:200]}")
