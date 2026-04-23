"""DEPRECATED — part_intro_writer는 figure_rationale로 교체되었습니다.

v1.0 변경 사항: 파트별 인트로(5개) 대신 코스당 1개의 "위인 선정 배경"
컴포넌트로 단순화. 아래 import 가드만 남겨두고, 실제 기능은
`backend.agents.figure_rationale`로 이동.
"""
from .figure_rationale import generate_rationale  # noqa: F401

# 구 API 호환이 필요하면 여기에 shim을 추가할 수 있음.
