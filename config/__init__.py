"""
config/__init__.py — 시스템 설정
"""
DEFAULT_CONFIG = {
    "llm_provider": "anthropic",
    "deep_think_llm": "claude-opus-4-6",            # Fund Manager
    "quick_think_llm": "claude-haiku-4-5-20251001", # Analysts
    "decision_llm": "claude-sonnet-4-6",            # Researcher, Trader, Risk
    "max_debate_rounds": 1,                         # Bull/Bear rounds
    "initial_capital": 100_000.0,
    "commission_rate": 0.001,
    "trading_days_interval": 1,
}


def get_config(overrides: dict = None) -> dict:
    """
    설정 반환 (오버라이드 지원)

    Args:
        overrides: 덮어쓸 설정 항목

    Returns:
        dict: 최종 설정 딕셔너리
    """
    cfg = DEFAULT_CONFIG.copy()
    if overrides:
        cfg.update(overrides)
    return cfg
