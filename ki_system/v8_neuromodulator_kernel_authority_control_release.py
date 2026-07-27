from __future__ import annotations
import math, os
VERSION = "neuromodulator_kernel_authority_control_v1"
SCOPE = {"compute_2ag_decay","compute_anandamide_level","compute_anandamide_ltd_value","compute_bdnf_state","compute_ei_balance","compute_phase6b_plasticity_adjustment"}
def _mode(name):
    if name not in SCOPE: return "old"
    return os.environ.get("BRAINSTEM_KERNEL_AUTH_" + name.upper(), "old").strip().lower()
def _finite(x):
    if isinstance(x,bool) or x is None or isinstance(x,str): return True
    if isinstance(x,(int,float)): return math.isfinite(float(x))
    if isinstance(x,dict): return all(_finite(v) for v in x.values())
    if isinstance(x,(list,tuple)): return all(_finite(v) for v in x)
    return True
def _equivalent(a,b,tol=1e-12):
    if isinstance(a,bool) or isinstance(b,bool): return a is b
    if isinstance(a,(int,float)) and isinstance(b,(int,float)): return math.isclose(float(a),float(b),rel_tol=tol,abs_tol=tol)
    if type(a) is not type(b): return False
    if isinstance(a,dict): return a.keys()==b.keys() and all(_equivalent(a[k],b[k],tol) for k in a)
    if isinstance(a,(list,tuple)): return len(a)==len(b) and all(_equivalent(x,y,tol) for x,y in zip(a,b))
    return a==b
def select_authoritative(name, old_output, kernel_output):
    if _mode(name)!="kernel_guarded": return old_output
    try:
        if not _finite(kernel_output): return old_output
        if not _equivalent(old_output,kernel_output): return old_output
        return kernel_output
    except Exception:
        return old_output
def selftest():
    assert select_authoritative("compute_2ag_decay",1.0,1.0)==1.0
    assert select_authoritative("outside",1,2)==1
    return {"status":"ok","version":VERSION,"default_authority":"old","scope":sorted(SCOPE)}
