
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from ki_system.autonomous import AutonomousLoop
d = {}
cyc = getattr(AutonomousLoop, "cycle", None)
run = getattr(AutonomousLoop, "run", None)
d["cycle_module"] = getattr(cyc, "__module__", None)
d["cycle_name"]   = getattr(cyc, "__name__", None)
d["run_module"]   = getattr(run, "__module__", None)
flags = {}
for k in dir(AutonomousLoop):
    if k.startswith("__"): continue
    try: v = getattr(AutonomousLoop, k)
    except Exception: continue
    if isinstance(v, (bool, str, int, float)): flags[k] = v
d["flags"] = flags
print(json.dumps(d, sort_keys=True))
