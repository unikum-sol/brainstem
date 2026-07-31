# -*- coding: utf-8 -*-
"""BrainStem-Systemtest fuer frische und bereits gelaufene Installationen.

Der Test initialisiert bei fehlender Datenbank ausschliesslich das Schema ueber
db_bootstrap. Er startet keinen Lernzyklus und erfindet keine Laufzeitwerte.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "ki_memory.sqlite3"


def _table_exists(con, table):
    return con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _columns(con, table):
    if not _table_exists(con, table):
        return set()
    return {row[1] for row in con.execute("PRAGMA table_info(" + table + ")").fetchall()}


def _count(con, table, where="", params=()):
    if not _table_exists(con, table):
        return None
    try:
        sql = "SELECT COUNT(*) FROM " + table
        if where:
            sql += " WHERE " + where
        return int(con.execute(sql, params).fetchone()[0])
    except Exception:
        return None


def _read_kv(con, table):
    if not _table_exists(con, table):
        return {}
    cols = _columns(con, table)
    if "key" not in cols or "value" not in cols:
        return {}
    try:
        return dict(con.execute("SELECT key,value FROM " + table).fetchall())
    except Exception:
        return {}


def _find_kv(con, keynames):
    wanted = {str(key).lower() for key in keynames}
    tables = [row[0] for row in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    for table in tables:
        values = _read_kv(con, table)
        for key, value in values.items():
            if str(key).lower() in wanted:
                return value
    return None


def _num(value):
    try:
        return float(value)
    except Exception:
        return None


def _show(value):
    return "noch nicht initialisiert" if value is None else str(value)


def _mark(ok):
    return "OK" if ok else "X"


def main():
    existed_before = DB.exists()

    from ki_system.db_bootstrap import ensure_database_exists
    bootstrap = ensure_database_exists(str(DB))

    con = sqlite3.connect(str(DB), timeout=30.0)
    con.row_factory = sqlite3.Row

    from ki_system.autonomous import AutonomousLoop as Loop
    import ki_system.phase_registry as registry

    cycle_module = getattr(Loop.cycle, "__module__", "") or ""
    expected_top = getattr(registry, "EXPECTED_TOP_MODULE", None)
    top_ok = bool(expected_top and cycle_module.endswith(expected_top))

    print("=" * 68)
    print("BRAINSTEM SYSTEMTEST - FRESH-TAKEOUT-KOMPATIBEL")
    print("=" * 68)

    print("\n[0] BOOTSTRAP")
    print("  DB vorher vorhanden:", existed_before)
    print("  DB erstellt:", bool(bootstrap.get("db_created")))
    print("  DB-Pfad:", bootstrap.get("db_path"))
    print("  Bootstrap-Fehler:", bootstrap.get("errors") or "keine")
    print("  neue Performance-Indizes:", bootstrap.get("perf_indexes_created") or "keine")

    print("\n[1] KETTE / KOMPASS")
    print("  cycle-Spitze:", cycle_module)
    print("  EXPECTED_TOP:", expected_top)
    print("  cycle auf EXPECTED_TOP:", top_ok)
    print("  7g/7f/7e/7d:",
          getattr(Loop, "phase7g_bdnf_growth_consolidation_release", False),
          getattr(Loop, "phase7f_orexin_wake_endurance_release", False),
          getattr(Loop, "phase7e_histamine_wake_arousal_release", False),
          getattr(Loop, "phase7d_slow_wave_sleep_substructure_release", False))
    print("  fact_promotion:", getattr(Loop, "fact_promotion", None))
    print("  no_word_blacklists:", getattr(Loop, "no_word_blacklists", None))

    print("\n[2] 7d SLOW-WAVE")
    p7d = _read_kv(con, "phase7d_slow_wave_params")
    s7d = _read_kv(con, "phase7d_state")
    for key in ("cycle_count", "total_slow_wave_sleeps", "total_reinforced",
                "total_weakened", "phase_version"):
        value = p7d.get(key, s7d.get(key))
        print("  " + key + ":", _show(value))

    cycles_7d = _count(
        con,
        "phase7d_slow_wave_cycles",
        "reason=?",
        ("self_regulating_slow_wave_sleep",),
    )
    selection_measured = bool(cycles_7d)
    selection_sharp = None
    if selection_measured:
        cols = _columns(con, "phase7d_slow_wave_cycles")
        needed = {"candidates_survived", "candidates_participated", "weakened",
                  "adaptive_threshold_avg"}
        if needed.issubset(cols):
            row = con.execute(
                "SELECT AVG(candidates_survived),AVG(candidates_participated),"
                "AVG(weakened),AVG(adaptive_threshold_avg) "
                "FROM phase7d_slow_wave_cycles WHERE reason=?",
                ("self_regulating_slow_wave_sleep",),
            ).fetchone()
            if row and row[0] is not None and row[1] is not None and row[2] is not None:
                print("  v2-Zyklen: %d | avg surv/part/weak/thr: %.2f / %.2f / %.2f / %.2f" %
                      (cycles_7d, row[0], row[1], row[2], row[3] or 0.0))
                selection_sharp = row[0] < row[1] and row[2] > 0
    if not selection_measured:
        print("  Laufzeitstatus: noch keine Slow-Wave-Zyklen")

    print("\n[3] REGULATOR-STATUS (nur gelesen)")
    state_tables = {
        "Histamin": "phase7e_histamine_state",
        "Orexin": "phase7f_orexin_state",
        "BDNF": "phase7g_bdnf_state",
        "Cortisol": "cortisol_state",
    }
    for label, table in state_tables.items():
        state = _read_kv(con, table)
        regime = state.get("last_regime")
        print("  %-9s regime: %s" % (label, _show(regime)))
    cort = _read_kv(con, "cortisol_state")
    print("  Cortisol stage:", _show(cort.get("stage")))
    print("  Cortisol last load:", _show(cort.get("last_allostatic_load")))

    print("\n[4] LESEABDECKUNG")
    total_chunks = _count(con, "chunks")
    covered = None
    if _table_exists(con, "chunk_attention_scores") and "chunk_id" in _columns(con, "chunk_attention_scores"):
        covered = con.execute(
            "SELECT COUNT(DISTINCT chunk_id) FROM chunk_attention_scores"
        ).fetchone()[0]
    if total_chunks is None:
        print("  keine Chunk-Tabelle vorhanden")
    elif total_chunks == 0:
        print("  Chunks: 0 (noch kein Corpus importiert)")
    else:
        covered = int(covered or 0)
        print("  Chunks gesamt:", total_chunks)
        print("  Abdeckungsindikator:", covered, "(%.1f%%)" % (100.0 * covered / total_chunks))
    pending = _count(con, "reading_queue", "LOWER(COALESCE(status,''))=?", ("pending",))
    print("  reading_queue pending:", _show(pending))

    print("\n[5] BOTENSTOFFE (#1-#12)")
    sleep = _read_kv(con, "phase6a_neuromodulated_sleep_state")
    values = {
        "dopamine": sleep.get("dopamine"),
        "serotonin": sleep.get("serotonin"),
        "noradrenaline": sleep.get("noradrenaline"),
        "acetylcholine": sleep.get("acetylcholine"),
        "glutamate": sleep.get("glutamate"),
        "gaba": sleep.get("gaba"),
        "adenosine": _find_kv(con, ("adenosine_level", "adenosine")),
        "endocannabinoid_2ag": _find_kv(con, ("endocannabinoid_2ag", "2ag_current", "two_ag_level")),
        "endocannabinoid_anandamide": _find_kv(con, ("endocannabinoid_anandamide", "anandamide_level", "anandamide")),
        "cortisol": cort.get("cortisol_level"),
        "histamine": sleep.get("histamine", _find_kv(con, ("histamine_level", "histamine"))),
        "orexin": sleep.get("orexin", _find_kv(con, ("orexin_level", "orexin"))),
        "bdnf": sleep.get("bdnf", _find_kv(con, ("bdnf_level", "bdnf"))),
    }
    initialized = []
    for key, value in values.items():
        present = value is not None
        initialized.append(present)
        print("  %-25s %s" % (key + ":", _show(value)))
    all_initialized = all(initialized)

    print("\n[6] SAFETY")
    safe = []
    for table in ("facts", "relations", "questions"):
        value = _count(con, table)
        safe.append(value if value is not None else -1)
    safe_ok = safe == [0, 0, 0]
    print("  facts/relations/questions:", safe)

    print("\n[7] REGISTRY")
    load_order = getattr(registry, "LOAD_ORDER", [])
    last = load_order[-1].get("label") if load_order else None
    print("  Eintraege:", len(load_order))
    print("  letzter:", last)
    print("  EXPECTED_TOP:", expected_top)

    bootstrap_ok = not bootstrap.get("errors")
    compass_ok = (
        getattr(Loop, "fact_promotion", None) == "disabled"
        and getattr(Loop, "direct_fact_writes", None) == "disabled"
        and getattr(Loop, "direct_relation_writes", None) == "disabled"
        and getattr(Loop, "no_word_blacklists", None) is True
    )

    print("\n" + "=" * 68)
    print("FAZIT")
    print("=" * 68)
    print("  [%s] Bootstrap / Schema" % _mark(bootstrap_ok))
    print("  [%s] 7cort ist Ketten-Spitze" % _mark(top_ok))
    print("  [%s] Kompass-Flags gesetzt" % _mark(compass_ok))
    print("  [%s] Uebergangssperre 0/0/0" % _mark(safe_ok))
    if selection_sharp is None:
        print("  [i] 7d-Selektion: noch keine Laufzeitdaten")
    else:
        print("  [%s] Selektion scharf (surv<part und weak>0)" % _mark(selection_sharp))
    if all_initialized:
        print("  [OK] Alle Botenstoffwerte initialisiert")
    else:
        print("  [i] Botenstoffwerte: frischer Zustand / noch nicht vollstaendig initialisiert")
    if not existed_before:
        print("  [i] Frischer Takeout: Datenbank wurde durch den Systemtest gebootstrapt")
    elif total_chunks == 0:
        print("  [i] Datenbank vorhanden, aber noch kein Corpus importiert")
    print("=" * 68)

    con.close()
    return 0 if (bootstrap_ok and top_ok and compass_ok and safe_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
