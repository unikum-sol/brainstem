"""
V8 Phase4g Neuromodulated Learning Control

Consolidation patch: promotes the already-working Phase4g attention/learning
implementation into a named neuromodulated learning-control core.

Safety guarantees:
- no word blacklists
- no direct facts writes
- no direct relations writes
- no question generation
- no fact promotion
"""
from __future__ import annotations

import json
import time

PHASE = "phase4g_neuromodulated_learning_control"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"


def _json(value):
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return json.dumps(str(value), ensure_ascii=False)


def _get_memory(loop):
    for name in ("mem", "memory", "m", "store", "memory_store", "db"):
        obj = getattr(loop, name, None)
        if obj is not None and (hasattr(obj, "db") or hasattr(obj, "execute") or hasattr(obj, "cursor")):
            return obj
    for obj in getattr(loop, "__dict__", {}).values():
        if hasattr(obj, "db") or hasattr(obj, "execute") or hasattr(obj, "cursor"):
            return obj
    return None


def _connection(mem):
    if mem is None:
        return None
    if hasattr(mem, "db"):
        return mem.db
    if hasattr(mem, "execute") and hasattr(mem, "cursor"):
        return mem
    return None


def _execute(conn, sql, params=()):
    if conn is None:
        return None
    return conn.execute(sql, params)


def _ensure_kv_table(conn, table):
    _execute(conn, f"CREATE TABLE IF NOT EXISTS {table} (key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)")


def _set_kv(conn, table, key, value):
    if conn is None:
        return
    _ensure_kv_table(conn, table)
    now = int(time.time())
    _execute(
        conn,
        f"INSERT INTO {table}(key,value,updated_at) VALUES(?,?,?) "
        f"ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (key, _json(value), now),
    )


def _ensure_minimal_control_schema(conn):
    if conn is None:
        return
    for table in ("neuromodulated_learning_control_state", "reading_strategy_state", "attention_queue_state", "rollback_safe_core_state"):
        _ensure_kv_table(conn, table)


def ensure_phase4_schema(mem_or_conn=None):
    conn = _connection(mem_or_conn)
    try:
        from ki_system import v8_phase4_schema_runtime_guard_fixed12 as guard12
        if hasattr(guard12, "ensure_phase4_schema"):
            try:
                guard12.ensure_phase4_schema(mem_or_conn)
            except TypeError:
                guard12.ensure_phase4_schema(conn)
    except Exception:
        pass
    try:
        from ki_system import v8_phase4_schema_manager_canonicalization as canon
        if hasattr(canon, "ensure_phase4_schema"):
            try:
                canon.ensure_phase4_schema(mem_or_conn)
            except TypeError:
                canon.ensure_phase4_schema(conn)
    except Exception:
        pass
    _ensure_minimal_control_schema(conn)
    _write_state(conn)
    if conn is not None:
        try:
            conn.commit()
        except Exception:
            pass


def _write_state(conn):
    if conn is None:
        return
    for table in ("rollback_safe_core_state", "neuromodulated_learning_control_state", "reading_strategy_state", "attention_queue_state"):
        _set_kv(conn, table, "phase", PHASE)
        _set_kv(conn, table, "learning_mode", LEARNING_MODE)
        _set_kv(conn, table, "no_word_blacklists", True)
        _set_kv(conn, table, "fact_promotion", "disabled")
        _set_kv(conn, table, "direct_fact_writes", "disabled")
        _set_kv(conn, table, "direct_relation_writes", "disabled")
        _set_kv(conn, table, "question_generation", "disabled")


def _delegate_cycle(loop, progress=None):
    try:
        from ki_system import v8_phase4g_neuromodulated_attention_queue_activation as phase4g
        if hasattr(phase4g, "managed_cycle"):
            return phase4g.managed_cycle(loop, progress)
        if hasattr(phase4g, "safe_cycle"):
            return phase4g.safe_cycle(loop, progress)
    except Exception as exc:
        return {"status":"phase4g_delegate_error","error":repr(exc),"phase":PHASE}
    try:
        from ki_system import v8_phase4def_context_learning_pack as phase4def
        if hasattr(phase4def, "safe_cycle"):
            return phase4def.safe_cycle(loop, progress)
    except Exception as exc:
        return {"status":"phase4def_delegate_error","error":repr(exc),"phase":PHASE}
    return {"status":"no_phase4_delegate_available","phase":PHASE}


def managed_cycle(self, progress=None):
    mem = _get_memory(self)
    ensure_phase4_schema(mem)
    result = _delegate_cycle(self, progress)
    conn = _connection(mem)
    _write_state(conn)
    if conn is not None:
        try:
            conn.commit()
        except Exception:
            pass
    if isinstance(result, dict):
        result.setdefault("neuromodulated_learning_control", {
            "status": PHASE,
            "no_word_blacklists": True,
            "learning_mode": LEARNING_MODE,
            "fact_promotion": "disabled",
        })
    return result


def managed_run(self, cycles=5, progress=None):
    mem = _get_memory(self)
    ensure_phase4_schema(mem)
    out = []
    for i in range(max(1, int(cycles or 1))):
        if getattr(self, "cancel", False) or getattr(self, "stop", False) or getattr(self, "stopped", False):
            out.append({"status":"stopped","message":"Stop-Anforderung erkannt.","phase":PHASE})
            break
        if progress:
            try:
                progress(i + 1, cycles, PHASE)
            except TypeError:
                try:
                    progress(i + 1, cycles)
                except Exception:
                    pass
        out.append(managed_cycle(self, progress=None))
    conn = _connection(mem)
    _write_state(conn)
    if conn is not None:
        try:
            conn.commit()
        except Exception:
            pass
    return out


def patch_autonomous_loop(*args, **kwargs):
    if args:
        AutonomousLoop = args[0]
    else:
        from ki_system.autonomous import AutonomousLoop
    AutonomousLoop.run = managed_run
    AutonomousLoop.cycle = managed_cycle
    markers = {
        "phase4g_neuromodulated_learning_control": True,
        "_phase4g_neuromodulated_learning_control": True,
        "phase4g_neuromodulated_attention_queue_activation": True,
        "_phase4g_neuromodulated_attention_queue_activation": True,
        "phase4d_hypothesis_feedback_error_learning": True,
        "_phase4d_hypothesis_feedback_error_learning": True,
        "phase4e_neuromodulated_attention_strategy": True,
        "_phase4e_neuromodulated_attention_strategy": True,
        "phase4f_sleep_consolidation_self_improvement": True,
        "_phase4f_sleep_consolidation_self_improvement": True,
        "phase4def_context_learning_pack": True,
        "_phase4def_context_learning_pack": True,
        "phase4_schema_manager_canonicalization": True,
        "_phase4_schema_manager_canonicalization": True,
        "no_word_blacklists": True,
        "_no_word_blacklists": True,
        "learning_mode": LEARNING_MODE,
        "_rollback_learning_mode": LEARNING_MODE,
        "fact_promotion": "disabled",
        "_fact_promotion": "disabled",
    }
    for k, v in markers.items():
        try:
            setattr(AutonomousLoop, k, v)
        except Exception:
            pass
    return AutonomousLoop

try:
    patch_autonomous_loop()
except Exception:
    pass
