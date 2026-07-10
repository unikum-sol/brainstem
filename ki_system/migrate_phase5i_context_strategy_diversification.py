import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from ki_system.v8_phase5i_outcome_driven_context_strategy_diversification_release import ensure_schema, apply_diversification
print('schema:',ensure_schema(None))
print('strategy:',apply_diversification(None))
