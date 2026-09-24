# -*- coding: utf-8 -*-
"V8 Phase 7d - Slow-Wave Sleep Substructure (self-regulating down-selection)."
from __future__ import annotations
import json, math, os, random, sqlite3, time
from pathlib import Path

PHASE = "phase7d_slow_wave_sleep_substructure_release"
PHASE_VERSION = "phase7d_v2_self_regulating"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"

SCHEMA_TABLES = {
    "phase7d_state": [("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
    "phase7d_slow_wave_params": [("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
    "phase7d_slow_wave_cycles": [
        ("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
        ("n_oscillations","INTEGER"),("adenosine_level","REAL"),("up_state_avg_activity","REAL"),
        ("down_state_scale","REAL"),("candidates_reactivated","INTEGER"),("candidates_survived","INTEGER"),
        ("anchors_interleaved","INTEGER"),("reinforced","INTEGER"),("weakened","INTEGER"),("reason","TEXT"),
        ("selection_pressure","REAL"),("adaptive_threshold_avg","REAL"),("pool_size","INTEGER"),("candidates_participated","INTEGER")],
    "phase7d_up_state_events": [
        ("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
        ("oscillation_index","INTEGER"),("source_table","TEXT"),("source_id","INTEGER"),
        ("activity_score","REAL"),("is_anchor","INTEGER"),("active_flag","INTEGER")],
    "phase7d_consolidation_survivors": [
        ("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
        ("source_table","TEXT"),("source_id","INTEGER"),("up_states_survived","INTEGER"),
        ("final_consistency","REAL"),("reinforced","INTEGER")],
}
SCHEMA_INDEXES = [
    ("idx_phase7d_cycles_cyc","phase7d_slow_wave_cycles","cycle_index"),
    ("idx_phase7d_upstate_cyc","phase7d_up_state_events","cycle_index"),
    ("idx_phase7d_survivors_cyc","phase7d_consolidation_survivors","cycle_index"),
]
SLOW_WAVE_PARAMS = {
    "n_oscillations": 5, "up_state_reactivation_size": 30, "down_state_scale": 0.9,
    "survival_threshold": 3, "anchor_interleave_ratio": 0.3, "activity_threshold": 0.5,
    "slow_wave_freq_hz": 0.8, "reinforce_delta": 0.02, "weaken_delta": 0.01,
    "adenosine_sleep_threshold": 0.5, "total_slow_wave_sleeps": 0,
    "total_reinforced": 0, "total_weakened": 0,
    "reactivation_pool_factor": 4.0, "survival_consistency_ratio": 0.6,
    "min_participation_ratio": 0.4, "activity_threshold_floor": 0.15,
    "selection_pressure_gaba_gain": 0.6, "selection_pressure_glu_gain": 0.4,
    "selection_pressure_base": 0.5,
    # BRAINSTEM_PHASE7D_CONTEXT_HYPOTHESES_NOVEL_QUOTA_V1 (23.09.2026):
    # Diagnose (diagnose_phase7d_source_table_distribution.py) belegte
    # empirisch, dass ueber 13.900 Survivor-Zeilen in
    # phase7d_consolidation_survivors ausschliesslich source_table=
    # 'phase5g_experiment_outcomes' sind, 0 mit source_table=
    # 'context_hypotheses'. Ursache: der Novel-Anteil des Pools wurde in
    # _build_candidate_pool() zuerst vollstaendig (LIMIT n_novel, ohne
    # Obergrenze) aus phase5g_experiment_outcomes gefuellt; der
    # context_hypotheses-Fallback wurde nur bei einem verbleibenden
    # Rest erreicht -- der bei einer dauerhaft weit groesseren
    # phase5g_experiment_outcomes-Tabelle (hier 574.683 Zeilen)
    # strukturell immer 0 war. Dadurch konnte context_hypotheses
    # (uncertain_hypothesis / uncertain_lexical_boundary) nie
    # konsolidiert werden, was wiederum die Stage-B-Graduierung (JOIN
    # auf genau source_table='context_hypotheses') dauerhaft auf 0
    # Kandidaten hielt, unabhaengig von Warm-up/Budget/Critic-Gate.
    # Loesungsprinzip uebertragen aus wissenschaftlicher Literatur
    # (Homeostatic structural plasticity, Butz & van Ooyen 2014;
    # Sinusoidally-modulated noise as slow-wave-sleep surrogate,
    # Watkins et al.; Biologically inspired sleep algorithm, Tadros et
    # al. 2020): eine dominante, hochverfuegbare Quelle darf eine
    # andere nicht dauerhaft aus der Konsolidierung verdraengen --
    # jede Quelle braucht eine garantierte Mindest-Quote statt einer
    # reinen Verfuegbarkeits-Kaskade. Dieser Parameter legt den Anteil
    # von n_novel fest, der context_hypotheses in jedem Zyklus
    # mindestens garantiert zur Verfuegung steht, unabhaengig davon,
    # wie viele Zeilen phase5g_experiment_outcomes liefert. Bewusst
    # per DB-Parameter (kein Hardcoding, keine Wort-/Inhaltsregel,
    # reine Pool-Zusammensetzung) -- ueber phase7d_slow_wave_params
    # zur Laufzeit justierbar.
    "context_hypotheses_min_novel_ratio": 0.3,
    # BRAINSTEM_PHASE7D_NOVEL_FAIRNESS_RECENTERING_V1 (23.09.2026):
    # Eine 40-Zyklen-Simulation NACH dem obigen Pool-Quota-Fix zeigte,
    # dass trotz garantierter Pool-Praesenz weiterhin 0 context_
    # hypotheses-Kandidaten reinforced wurden. Ursache isoliert:
    # phase5g_experiment_outcomes-Kandidaten erhalten base_score=1-score,
    # wobei score bewusst die niedrigsten Werte der Tabelle sind (ORDER
    # BY ASC) -- bei grossen Tabellen liegt dieser Score
    # ordnungsstatistisch nahe 0, der abgeleitete base_score also nahe
    # 1.0 (gemessen: 0.989 bei n=5000, k=58). context_hypotheses (sowohl
    # Fallback als auch reaktivierte Kandidaten) erhalten dagegen einen
    # festen base_score von 0.5. Da alle Kandidaten in derselben
    # Aktivitaetsschwellen-Konkurrenz gegeneinander antreten, verlieren
    # context_hypotheses dadurch strukturell fast immer -- unabhaengig
    # von der Pool-Praesenz. Fix: Gruppenmittelwert des base_score wird
    # PRO source_table (Anchors ausgenommen, deren +0.12-Bonus bewusst
    # bleibt) auf einen gemeinsamen Zielwert zentriert -- rein additive
    # Verschiebung, interne Rangfolge je Quelle bleibt unveraendert, die
    # fachliche "schwache Experimente zuerst"-Regel von
    # phase5g_experiment_outcomes bleibt inhaltlich unangetastet.
    # enabled=0.0 reproduziert das alte (unfaire) Verhalten exakt --
    # jederzeit per DB-Parameter rueckgaengig machbar, kein Hardcoding.
    #
    # BRAINSTEM_PHASE7D_NOVEL_FAIRNESS_ARCHITECTURE_INTEGRATION_V1
    # (23.09.2026, Nachtrag): die beiden obigen Keys (enabled/target)
    # waren als isolierter, lokaler An/Aus-Schalter in Phase 7d selbst
    # implementiert -- funktional korrekt (mehrfach verifiziert), aber
    # architektonisch NICHT im Einklang mit dem Rest dieses Projekts:
    # jeder andere selbstregulierende Mechanismus (Lernrate,
    # Explorations-/Inhibitions-/Revisions-Bias, novel_ratio_*,
    # gaba_novel_inhibition usw.) lebt zentral in
    # phase6c_meta_control_parameters, wird dort neuromodulator-gegated
    # UND anhand eines GEMESSENEN Treibers reguliert (nicht als fixer
    # Konstantwert), erhaelt automatisch adaptive Min/Max-Grenzen
    # (phase7c) und eigene Meta-Metaplastizitaet/Saettigungsschutz
    # (phase6d). Ein isolierter, statischer Bool+Fixwert allein in Phase
    # 7d haette genau diese drei Eigenschaften NICHT gehabt.
    #
    # Die eigentliche Korrekturstaerke wird deshalb jetzt primaer aus dem
    # neuen, dort registrierten Meta-Parameter
    # phase6c_meta_control_parameters.novel_fairness_recenter_strength
    # gelesen (siehe v8_phase6c_..._release.py:
    # META_PARAMETER_DEFAULTS -- default 0.85, Grenzen [0.0,1.0],
    # gaba-gegated, reguliert anhand des GEMESSENEN
    # 'context_fairness_gap', nicht anhand einer Annahme). Die beiden
    # lokalen Keys hier bleiben NUR als Fallback erhalten (Abwaerts-
    # kompatibilitaet, falls phase6c aus irgendeinem Grund noch nicht
    # gelaufen ist / die Tabelle fehlt) -- siehe
    # _read_novel_fairness_strength() weiter unten. Kein Verhaltens-
    # Bruch: default 0.85 des neuen Parameters entspricht praktisch
    # demselben Korrekturgrad wie das zuvor validierte enabled=1.0/
    # target=0.5, nur jetzt selbstregulierend statt fest.
    "novel_fairness_recentering_enabled": 1.0,
    "novel_fairness_recenter_target": 0.5,
}

def _now(): return int(time.time())
def _clamp(x, lo=0.0, hi=1.0):
    try: x = float(x)
    except Exception: x = 0.0
    if x < lo: return lo
    if x > hi: return hi
    return x
def _to_float(x, d=0.0):
    try: return float(x)
    except Exception: return d
def _to_int(x, d=0):
    try: return int(x)
    except Exception: return d
def _table_exists(con, t): return con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None
def _index_exists(con, i): return con.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (i,)).fetchone() is not None
def _columns(con, t):
    if not _table_exists(con, t): return []
    return [r[1] for r in con.execute("PRAGMA table_info(" + t + ")").fetchall()]

def _quantile(sorted_vals, p):
    n = len(sorted_vals)
    if n == 0: return 0.0
    p = _clamp(p, 0.0, 1.0)
    if n == 1: return float(sorted_vals[0])
    idx = p * (n - 1)
    lo = int(idx); hi = min(lo + 1, n - 1); frac = idx - lo
    return float(sorted_vals[lo]) * (1.0 - frac) + float(sorted_vals[hi]) * frac

def resolve_db(obj=None):
    if obj is None:
        path = "ki_memory.sqlite3"
        if not os.path.exists(path):
            cand = Path(__file__).resolve().parent.parent / "ki_memory.sqlite3"
            if cand.exists(): path = str(cand)
        con = sqlite3.connect(path, timeout=30.0); con.row_factory = sqlite3.Row; return con
    if isinstance(obj, sqlite3.Connection):
        obj.row_factory = sqlite3.Row; return obj
    for a in ("db", "connection", "conn", "memory"):
        inner = getattr(obj, a, None)
        if inner is None: continue
        if isinstance(inner, sqlite3.Connection):
            inner.row_factory = sqlite3.Row; return inner
        inner2 = getattr(inner, "db", None) or getattr(inner, "connection", None)
        if isinstance(inner2, sqlite3.Connection):
            inner2.row_factory = sqlite3.Row; return inner2
    return resolve_db(None)

def ensure_schema(con):
    rep = {"created_tables": [], "added_columns": [], "created_indexes": []}
    for t, cols in SCHEMA_TABLES.items():
        if not _table_exists(con, t):
            con.execute("CREATE TABLE " + t + " (" + ", ".join(n + " " + s for n, s in cols) + ")")
            rep["created_tables"].append(t)
        else:
            ex = set(_columns(con, t))
            for n, s in cols:
                if n in ex: continue
                su = s.upper()
                if "PRIMARY KEY" in su or "AUTOINCREMENT" in su: continue
                con.execute("ALTER TABLE " + t + " ADD COLUMN " + n + " " + s); rep["added_columns"].append(t + "." + n)
    for i, t, c in SCHEMA_INDEXES:
        if not _index_exists(con, i):
            con.execute("CREATE INDEX " + i + " ON " + t + "(" + c + ")"); rep["created_indexes"].append(i)
    con.commit(); return rep

def _self_check_schema(con):
    m = []
    for t, cols in SCHEMA_TABLES.items():
        ex = set(_columns(con, t))
        for n, _s in cols:
            if n not in ex: m.append(t + "." + n)
    return m

def _kv_set(con, table, key, value):
    if not _table_exists(con, table): return
    tc = set(_columns(con, table))
    if "key" not in tc or "value" not in tc: return
    v = ("true" if value else "false") if isinstance(value, bool) else str(value)
    con.execute("INSERT INTO " + table + "(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at", (key, v, _now()))

def _read_kv(con, table):
    if not _table_exists(con, table): return {}
    tc = set(_columns(con, table))
    if "key" not in tc or "value" not in tc: return {}
    return dict(con.execute("SELECT key,value FROM " + table).fetchall())

def _read_neuromod(con):
    st = _read_kv(con, "phase6a_neuromodulated_sleep_state")
    ei = _read_kv(con, "phase7c_state")
    return {
        "dopamine": _clamp(_to_float(st.get("dopamine"), 0.5)),
        "serotonin": _clamp(_to_float(st.get("serotonin"), 0.5)),
        "noradrenaline": _clamp(_to_float(st.get("noradrenaline"), 0.5)),
        "acetylcholine": _clamp(_to_float(st.get("acetylcholine"), 0.5)),
        "glutamate": _clamp(_to_float(ei.get("glutamate_state", st.get("glutamate")), 0.5)),
        "gaba": _clamp(_to_float(ei.get("gaba_state", st.get("gaba")), 0.3)),
    }

def initialize_slow_wave_parameters(con):
    ensure_schema(con); ins = []
    for k, v in SLOW_WAVE_PARAMS.items():
        if con.execute("SELECT value FROM phase7d_slow_wave_params WHERE key=?", (k,)).fetchone() is None:
            _kv_set(con, "phase7d_slow_wave_params", k, v); ins.append(k)
    con.commit(); return {"inserted": ins, "total": len(SLOW_WAVE_PARAMS)}

def _get_sw(con, key, d=0.0):
    return _to_float(_read_kv(con, "phase7d_slow_wave_params").get(key), d)
def _set_sw(con, key, value): _kv_set(con, "phase7d_slow_wave_params", key, value)

def _get_adenosine_level(con):
    if not _table_exists(con, "phase7a_adenosine_state"): return 0.0
    r = con.execute("SELECT value FROM phase7a_adenosine_state WHERE key='adenosine_level'").fetchone()
    return _to_float(r[0], 0.0) if r else 0.0

def _read_novel_fairness_strength(con, local_enabled, local_target):
    # BRAINSTEM_PHASE7D_NOVEL_FAIRNESS_ARCHITECTURE_INTEGRATION_V1:
    # primary source of truth is the self-regulating meta-parameter in
    # phase6c (neuromodulator-gated, measured-metric-driven, adaptive
    # boundaries via phase7c, meta-metaplasticity via phase6d). Falls
    # back to the local, static phase7d_slow_wave_params keys ONLY if
    # phase6c's table or this specific row does not exist yet (e.g.
    # phase6c has not run once, or an older/partial database) -- this
    # keeps Phase 7d fully functional standalone, matching this
    # project's "no hard dependency between phase modules" discipline.
    if _table_exists(con, "phase6c_meta_control_parameters"):
        row = con.execute(
            "SELECT current_value FROM phase6c_meta_control_parameters "
            "WHERE parameter_key='novel_fairness_recenter_strength'"
        ).fetchone()
        if row is not None and row[0] is not None:
            return _clamp(_to_float(row[0], 0.85), 0.0, 1.0), "phase6c_meta_control_parameters"
    # Fallback matches the exact, previously validated static behavior:
    # local_enabled=1.0 -> strength=1.0 (full mean-centering, identical
    # to the first delivered fix), local_enabled=0.0 -> strength=0.0
    # (original, pre-fix behavior). local_target itself is used
    # separately as target_mean by the caller, never folded in here.
    fallback_strength = 1.0 if bool(local_enabled) else 0.0
    return fallback_strength, "phase7d_local_fallback"


def _recenter_novel_fairness(pool_items, target_mean=0.5, strength=0.85):
    # BRAINSTEM_PHASE7D_NOVEL_FAIRNESS_RECENTERING_V1: neutralize a
    # purely statistical group-level base_score offset between pool
    # sources (see SLOW_WAVE_PARAMS comment for the full measured
    # background) BEFORE candidates enter the shared activity-threshold
    # competition. Anchors (is_anchor=True) are intentionally excluded:
    # their +0.12 activity bonus and stability-derived base_score are a
    # deliberate, already-reviewed preference for consolidated
    # knowledge, not the asymmetry this fix targets. Recentering is a
    # pure additive shift per source_table group -- it preserves each
    # group's own internal ranking (which candidate within that group
    # is most/least favored) completely unchanged; it only removes the
    # cross-group mean offset so no single source can structurally
    # dominate the pool's reinforcement competition purely because of
    # how its own scoring formula happens to be centered.
    #
    # BRAINSTEM_PHASE7D_NOVEL_FAIRNESS_ARCHITECTURE_INTEGRATION_V1
    # (Nachtrag): `enabled` (bool) wurde durch `strength` (float,
    # [0.0,1.0]) ersetzt, damit der Grad der Korrektur kontinuierlich
    # und selbstregulierend statt binaer ist -- strength=0.0 entspricht
    # exakt dem alten "enabled=False" (kein Shift), strength=1.0 dem
    # alten "enabled=True" (voller Shift auf target_mean); Werte
    # dazwischen sind eine PARTIELLE Korrektur, wie sie der neue,
    # adaptive phase6c-Meta-Parameter novel_fairness_recenter_strength
    # tatsaechlich liefert.
    strength = _clamp(_to_float(strength, 0.85), 0.0, 1.0)
    if strength <= 0.0:
        return
    groups = {}
    for it in pool_items:
        if it.get("is_anchor"):
            continue
        groups.setdefault(it["source_table"], []).append(it)
    for items in groups.values():
        if not items:
            continue
        vals = [it["base_score"] for it in items]
        group_mean = sum(vals) / len(vals)
        shift = (target_mean - group_mean) * strength
        if abs(shift) < 1e-12:
            continue
        for it in items:
            it["base_score"] = _clamp(it["base_score"] + shift)


def _build_candidate_pool(con, pool_size, anchor_ratio, context_hypotheses_min_novel_ratio=0.3,
                           novel_fairness_recentering_enabled=True, novel_fairness_recenter_target=0.5):
    # NOTE: novel_fairness_recentering_enabled/_target parameter names
    # are kept for call-site backward compatibility (see
    # _run_slow_wave_sleep()); the actual correction STRENGTH used below
    # is resolved via _read_novel_fairness_strength(), which prefers the
    # adaptive phase6c meta-parameter over these two legacy arguments.
    # BRAINSTEM_PHASE7D_THREE_TRACK_REACTIVATION_V1
    n_anchor_target = int(pool_size * anchor_ratio)
    n_novel = pool_size - n_anchor_target
    out = []
    used_context_ids = set()

    # BRAINSTEM_PHASE7D_CONTEXT_HYPOTHESES_NOVEL_QUOTA_V1: guarantee a
    # minimum share of the novel slots for the context_hypotheses
    # fallback further below, regardless of how many rows
    # phase5g_experiment_outcomes can supply (see SLOW_WAVE_PARAMS
    # comment for the full diagnostic background and rationale).
    ratio = _clamp(_to_float(context_hypotheses_min_novel_ratio, 0.3), 0.0, 1.0)
    n_context_reserved = min(n_novel, int(math.ceil(n_novel * ratio)))
    n_novel_phase5g_cap = max(0, n_novel - n_context_reserved)

    anchor_rows = []
    if _table_exists(con, "phase6b_anchor_pool"):
        anchor_rows = con.execute(
            "SELECT id,stability_score FROM phase6b_anchor_pool "
            "WHERE active=1 ORDER BY stability_score DESC,last_replayed_at ASC LIMIT ?",
            (n_anchor_target,),
        ).fetchall()
        for row in anchor_rows:
            out.append({"source_table": "phase6b_anchor_pool",
                        "source_id": _to_int(row[0]),
                        "is_anchor": True,
                        "base_score": _clamp(_to_float(row[1], 0.5))})

    state = _read_kv(con, "phase7d_state")
    phase6b_state = _read_kv(con, "phase6b_state")
    current_cycle = _to_int(state.get("cycle_count"), 0) + 1
    checkpoint = _to_int(phase6b_state.get("phase7d_survivor_anchor_checkpoint_id"), 0)
    reactivation_capacity = max(0, n_anchor_target - len(anchor_rows))
    reactivated = []

    if (reactivation_capacity > 0 and checkpoint > 0 and
            _table_exists(con, "phase7d_consolidation_survivors")):
        active_anchor_sources = set()
        if _table_exists(con, "phase6b_anchor_pool"):
            active_anchor_sources = {
                _to_int(row[0]) for row in con.execute(
                    "SELECT source_id FROM phase6b_anchor_pool "
                    "WHERE active=1 AND source_table='context_hypotheses'"
                ).fetchall()
            }

        candidates_by_level = {2: [], 1: []}
        rows = con.execute(
            "SELECT source_id,COUNT(DISTINCT cycle_index) AS survived_cycles,"
            "MAX(cycle_index) AS last_cycle "
            "FROM phase7d_consolidation_survivors "
            "WHERE id>? AND reinforced=1 AND source_table='context_hypotheses' "
            "GROUP BY source_id "
            "HAVING COUNT(DISTINCT cycle_index) IN (1,2) AND MAX(cycle_index)<?",
            (checkpoint, current_cycle),
        ).fetchall()
        for source_id, survived_cycles, last_cycle in rows:
            sid = _to_int(source_id)
            level = _to_int(survived_cycles)
            if sid not in active_anchor_sources and level in candidates_by_level:
                candidates_by_level[level].append((sid, _to_int(last_cycle)))

        slots_left = reactivation_capacity
        for level in (2, 1):
            if slots_left <= 0:
                break
            candidates = sorted(candidates_by_level[level], key=lambda item: item[0])
            if not candidates:
                continue
            cursor_key = "survivor_reactivation_cursor_n" + str(level)
            cursor = _to_int(state.get(cursor_key), 0)
            ordered = [item for item in candidates if item[0] > cursor]
            ordered.extend(item for item in candidates if item[0] <= cursor)
            chosen = ordered[:slots_left]
            for sid, last_cycle in chosen:
                reactivated.append({"source_table": "context_hypotheses",
                                    "source_id": sid,
                                    "is_anchor": False,
                                    "base_score": 0.5})
                used_context_ids.add(sid)
            if chosen:
                _kv_set(con, "phase7d_state", cursor_key, chosen[-1][0])
            slots_left -= len(chosen)

    out.extend(reactivated)

    novel = []
    if n_novel_phase5g_cap > 0 and _table_exists(con, "phase5g_experiment_outcomes"):
        c = set(_columns(con, "phase5g_experiment_outcomes"))
        sc = "effectiveness_score" if "effectiveness_score" in c else ("outcome_score" if "outcome_score" in c else None)
        idc = "id" if "id" in c else "rowid"
        sql = "SELECT " + idc + ((", " + sc) if sc else "") + " FROM phase5g_experiment_outcomes "
        if sc:
            sql += "ORDER BY " + sc + " ASC "
        sql += "LIMIT ?"
        for row in con.execute(sql, (n_novel_phase5g_cap,)).fetchall():
            base = _clamp(1.0 - _to_float(row[1], 0.5)) if sc else 0.5
            novel.append({"source_table": "phase5g_experiment_outcomes",
                          "source_id": _to_int(row[0]),
                          "is_anchor": False,
                          "base_score": base})

    remaining = max(0, n_novel - len(novel))
    if remaining > 0 and _table_exists(con, "context_hypotheses"):
        cursor = _to_int(state.get("context_fallback_cursor"), 0)
        if cursor <= 0 and _table_exists(con, "phase7d_up_state_events"):
            prior = con.execute(
                "SELECT MAX(source_id) FROM phase7d_up_state_events "
                "WHERE source_table='context_hypotheses'"
            ).fetchone()
            cursor = _to_int(prior[0], 0) if prior else 0

        max_row = con.execute("SELECT COALESCE(MAX(id),0) FROM context_hypotheses").fetchone()
        max_id = _to_int(max_row[0] if max_row else 0, 0)

        # BRAINSTEM_LEXICAL_LAYER_POOL_ISOLATION_V1
        #
        # The new 'uncertain_lexical_boundary' hypothesis role (see
        # v8_phase0_lexical_boundary_observation_release.py) is written
        # into this SAME, shared context_hypotheses table. Without an
        # explicit guard, the rotating novel-fallback scanner below (which
        # otherwise has no role filter at all) would immediately start
        # mixing lexical-boundary candidates into the SAME slow-wave
        # consolidation pool as sentence hypotheses -- violating this
        # project's own shadow-first activation discipline for a
        # brand-new hypothesis class. Gated by phase7d_state key
        # 'lexical_boundary_pool_isolated' (Python-level default "true"
        # via .get(), matching the exact convention already used elsewhere
        # in this same function for cross-phase state reads, e.g.
        # phase6b_state.phase7d_survivor_anchor_checkpoint_id above --
        # requires no explicit DB seeding). Flip to "false" via
        # activate_lexical_layer_step4.py only after a dedicated review of
        # the observe-only data.
        #
        # IMPLEMENTATION NOTE (revised after real end-to-end testing): an
        # earlier version of this fix filtered the already-collected `ids`
        # list AFTER scanning, leaving the scan's own WHERE clause
        # untouched. A full, real, multi-cycle baseline-comparison test
        # (running an identical synthetic corpus through the complete,
        # unmodified phase chain with and without this module) proved that
        # approach insufficient: because lexical-boundary rows share the
        # SAME id-space as sentence hypotheses and vastly outnumber them,
        # the rotating cursor's FIXED-SIZE per-cycle scan window (bounded
        # by `remaining`) would mostly land on stretches of now-excluded
        # lexical ids, taking many extra cycles to complete a full "lap"
        # back around to genuine sentence-hypothesis ids -- observed
        # directly as several consecutive "empty_pool" real cycles that do
        # NOT occur without this module present. The correct fix is to
        # exclude lexical-boundary rows directly in the scan's own WHERE
        # clause (below), so the scanner behaves exactly as if only
        # sentence hypotheses existed in the id-space, regardless of how
        # many lexical rows are interleaved -- SQLite's existing index on
        # context_hypotheses.role (see db_bootstrap.py's SCHEMA_INDEXES)
        # makes this an efficient, ordinary indexed skip, not a full scan.
        # With this fix, no post-filtering and no special cursor-
        # persistence casing are needed at all -- the surrounding cursor-
        # advancement/wrap-around/safety-cap logic and its persistence
        # (`ids[-1]`) are left completely UNCHANGED from the original,
        # since `ids` only ever contains genuinely-eligible ids to begin
        # with. Re-verified: the same baseline-comparison test now shows
        # IDENTICAL Phase 7d participation/survivor counts, cycle for
        # cycle, whether Phase 0 is present (isolated) or entirely absent.
        isolate_lexical = str(state.get("lexical_boundary_pool_isolated", "true")).strip().lower() != "false"
        role_filter_sql = " AND (role IS NULL OR role<>'uncertain_lexical_boundary')" if isolate_lexical else ""

        ids = []
        scan_cursor = cursor
        wrapped = False
        examined = 0
        while len(ids) < remaining and max_id > 0 and examined < max_id:
            row = con.execute(
                "SELECT id FROM context_hypotheses WHERE id>?" + role_filter_sql + " ORDER BY id LIMIT 1",
                (scan_cursor,),
            ).fetchone()
            if row is None:
                if wrapped:
                    break
                scan_cursor = 0
                wrapped = True
                continue
            sid = _to_int(row[0])
            scan_cursor = sid
            examined += 1
            if sid not in used_context_ids:
                ids.append(sid)
                used_context_ids.add(sid)

        for sid in ids:
            novel.append({"source_table": "context_hypotheses",
                          "source_id": sid,
                          "is_anchor": False,
                          "base_score": 0.5})
        if ids:
            _kv_set(con, "phase7d_state", "context_fallback_cursor", ids[-1])
            _kv_set(con, "phase7d_state", "context_fallback_sampler", "rotating_id_cursor_v1")
            _kv_set(con, "phase7d_state", "context_fallback_batch_size", len(ids))

    out.extend(novel)

    resolved_strength, strength_source = _read_novel_fairness_strength(
        con, novel_fairness_recentering_enabled, novel_fairness_recenter_target
    )
    _recenter_novel_fairness(
        out,
        target_mean=_clamp(_to_float(novel_fairness_recenter_target, 0.5)),
        strength=resolved_strength,
    )
    _kv_set(con, "phase7d_state", "novel_fairness_strength_applied", resolved_strength)
    _kv_set(con, "phase7d_state", "novel_fairness_strength_source", strength_source)

    _kv_set(con, "phase7d_state", "three_track_pool", "anchor_survivor_novel_v1")
    _kv_set(con, "phase7d_state", "reactivation_capacity", reactivation_capacity)
    _kv_set(con, "phase7d_state", "reactivation_selected", len(reactivated))
    _kv_set(con, "phase7d_state", "novel_selected", len(novel))
    _kv_set(con, "phase7d_state", "anchor_selected", len(anchor_rows))
    return out

def _run_slow_wave_sleep(con, cycle_index, neuromod, adenosine_level):
    n_osc = int(_get_sw(con, "n_oscillations", 5)); size = int(_get_sw(con, "up_state_reactivation_size", 30))
    anchor_ratio = _get_sw(con, "anchor_interleave_ratio", 0.3); down_scale = _get_sw(con, "down_state_scale", 0.9)
    reinforce_delta = _get_sw(con, "reinforce_delta", 0.02); weaken_delta = _get_sw(con, "weaken_delta", 0.01)
    pool_factor = _get_sw(con, "reactivation_pool_factor", 4.0)
    surv_ratio = _get_sw(con, "survival_consistency_ratio", 0.6)
    min_part_ratio = _get_sw(con, "min_participation_ratio", 0.4)
    thr_floor = _get_sw(con, "activity_threshold_floor", 0.15)
    sp_base = _get_sw(con, "selection_pressure_base", 0.5)
    sp_gaba = _get_sw(con, "selection_pressure_gaba_gain", 0.6)
    sp_glu = _get_sw(con, "selection_pressure_glu_gain", 0.4)
    ctx_min_novel_ratio = _get_sw(con, "context_hypotheses_min_novel_ratio", 0.3)
    fairness_enabled = _get_sw(con, "novel_fairness_recentering_enabled", 1.0) != 0.0
    fairness_target = _get_sw(con, "novel_fairness_recenter_target", 0.5)
    now = _now(); rnd = random.Random(now + cycle_index * 7919)
    glu = neuromod["glutamate"]; gaba = neuromod["gaba"]
    # self-regulating selection pressure from the system's own neuromodulator state
    sel_pressure = _clamp(sp_base + sp_gaba * gaba - sp_glu * glu)
    pool_size = max(size, int(size * pool_factor))
    pool = _build_candidate_pool(con, pool_size, anchor_ratio, ctx_min_novel_ratio,
                                  fairness_enabled, fairness_target)
    if not pool:
        con.execute("INSERT INTO phase7d_slow_wave_cycles(created_at,cycle_index,n_oscillations,adenosine_level,up_state_avg_activity,down_state_scale,candidates_reactivated,candidates_survived,anchors_interleaved,reinforced,weakened,reason,selection_pressure,adaptive_threshold_avg,pool_size,candidates_participated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (now, int(cycle_index), n_osc, float(adenosine_level), 0.0, float(down_scale), 0, 0, 0, 0, 0, "empty_pool", float(sel_pressure), 0.0, pool_size, 0))
        _set_sw(con, "total_slow_wave_sleeps", int(_get_sw(con, "total_slow_wave_sleeps", 0)) + 1); con.commit()
        return {"n_oscillations": n_osc, "pool_size": pool_size, "candidates": 0, "survivors": 0, "reinforced": 0, "weakened": 0, "anchors_interleaved": 0, "selection_pressure": round(sel_pressure,4), "adaptive_threshold_avg": 0.0, "up_state_avg_activity": 0.0, "reason": "empty_pool"}
    participation = {}; active_cnt = {}; meta = {}; anchors_interleaved = 0; thresholds = []
    for osc in range(1, n_osc + 1):
        acts = []
        for it in pool:
            noise = (rnd.random() - 0.5) * 0.3
            a = _clamp(it["base_score"] * (0.6 + 0.5 * glu) * (1.0 - 0.3 * gaba) + noise + (0.12 if it["is_anchor"] else 0.0))
            acts.append((it, a))
        # Efraimidis-Spirakis weighted sampling without replacement
        keyed = [(rnd.random() ** (1.0 / max(1e-6, a)), it, a) for (it, a) in acts]
        keyed.sort(key=lambda x: x[0], reverse=True)
        selected = keyed[:size]
        sel_acts = sorted(a for (_k, _it, a) in selected)
        threshold = max(thr_floor, _quantile(sel_acts, sel_pressure)); thresholds.append(threshold)
        for _k, it, a in selected:
            key = (it["source_table"], it["source_id"])
            if it["is_anchor"]: anchors_interleaved += 1
            participation[key] = participation.get(key, 0) + 1
            act = 1 if a >= threshold else 0
            if act: active_cnt[key] = active_cnt.get(key, 0) + 1
            meta[key] = {"is_anchor": it["is_anchor"], "last_activity": a}
            con.execute("INSERT INTO phase7d_up_state_events(created_at,cycle_index,oscillation_index,source_table,source_id,activity_score,is_anchor,active_flag) VALUES(?,?,?,?,?,?,?,?)",
                        (now, int(cycle_index), osc, it["source_table"], int(it["source_id"]), float(a), 1 if it["is_anchor"] else 0, act))
    min_part = max(1, int(round(min_part_ratio * n_osc)))
    reinforced = 0; weakened = 0; survivors = []
    for key, part in participation.items():
        st, sid = key; ac = active_cnt.get(key, 0); consistency = ac / max(1, part)
        if part >= min_part and consistency >= surv_ratio:
            reinforced += 1; survivors.append(key)
            if st == "phase6b_anchor_pool" and _table_exists(con, "phase6b_anchor_pool"):
                con.execute("UPDATE phase6b_anchor_pool SET stability_score=MIN(1.0,COALESCE(stability_score,0)+?) WHERE id=?", (reinforce_delta, int(sid)))
            con.execute("INSERT INTO phase7d_consolidation_survivors(created_at,cycle_index,source_table,source_id,up_states_survived,final_consistency,reinforced) VALUES(?,?,?,?,?,?,1)",
                        (now, int(cycle_index), st, int(sid), int(ac), float(consistency)))
        else:
            weakened += 1
            if st == "phase6b_anchor_pool" and _table_exists(con, "phase6b_anchor_pool"):
                con.execute("UPDATE phase6b_anchor_pool SET stability_score=MAX(0.0,COALESCE(stability_score,0)-?) WHERE id=?", (weaken_delta, int(sid)))
    up_avg = sum(m["last_activity"] for m in meta.values()) / max(1, len(meta))
    thr_avg = sum(thresholds) / max(1, len(thresholds))
    con.execute("INSERT INTO phase7d_slow_wave_cycles(created_at,cycle_index,n_oscillations,adenosine_level,up_state_avg_activity,down_state_scale,candidates_reactivated,candidates_survived,anchors_interleaved,reinforced,weakened,reason,selection_pressure,adaptive_threshold_avg,pool_size,candidates_participated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (now, int(cycle_index), n_osc, float(adenosine_level), float(up_avg), float(down_scale), len(participation), len(survivors), anchors_interleaved, reinforced, weakened, "self_regulating_slow_wave_sleep", float(sel_pressure), float(thr_avg), pool_size, len(participation)))
    _set_sw(con, "total_slow_wave_sleeps", int(_get_sw(con, "total_slow_wave_sleeps", 0)) + 1)
    _set_sw(con, "total_reinforced", int(_get_sw(con, "total_reinforced", 0)) + reinforced)
    _set_sw(con, "total_weakened", int(_get_sw(con, "total_weakened", 0)) + weakened)
    con.commit()
    return {"n_oscillations": n_osc, "pool_size": pool_size, "candidates": len(participation), "survivors": len(survivors),
            "reinforced": reinforced, "weakened": weakened, "anchors_interleaved": anchors_interleaved,
            "selection_pressure": round(sel_pressure, 4), "adaptive_threshold_avg": round(thr_avg, 4), "up_state_avg_activity": round(up_avg, 4)}

def run_phase7d_cycle(db_or_obj=None, cycle_index=None):
    con = resolve_db(db_or_obj); ensure_schema(con)
    missing = _self_check_schema(con)
    if missing: return {"phase": PHASE, "status": "schema_check_failed", "missing_columns": missing}
    initialize_slow_wave_parameters(con)
    if cycle_index is None:
        cycle_index = _to_int(_read_kv(con, "phase7d_state").get("cycle_count"), 0) + 1
    neuromod = _read_neuromod(con); ade = _get_adenosine_level(con)
    phase7a_state = _read_kv(con, "phase7a_adenosine_state") if _table_exists(con, "phase7a_adenosine_state") else {}
    canonical_mode = str(phase7a_state.get("homeostat_mode", "wake")).strip().lower()
    cooperative_state = _read_kv(con, "cooperative_sleep_wake_state") if _table_exists(con, "cooperative_sleep_wake_state") else {}
    cooperative_mode = str(cooperative_state.get("state", "wake")).strip().lower()
    if canonical_mode == "sleep" or cooperative_mode == "sleep":
        sw = _run_slow_wave_sleep(con, cycle_index, neuromod, ade); status = "slow_wave_sleep_executed"
        sw["entry_authority"] = "cooperative" if cooperative_mode == "sleep" else "adenosine_homeostat"
    else:
        sw = {"skipped": True, "reason": "canonical_and_cooperative_modes_are_wake", "adenosine": ade,
              "canonical_homeostat_mode": canonical_mode, "cooperative_mode": cooperative_mode}; status = "awake_no_slow_wave"
    for k, v in [("cycle_count", cycle_index), ("last_cycle_at", _now()), ("phase", PHASE), ("phase_version", PHASE_VERSION),
                 ("learning_mode", LEARNING_MODE), ("no_word_blacklists", True), ("direct_fact_writes", "disabled"),
                 ("direct_relation_writes", "disabled"), ("fact_promotion", "disabled"), ("slow_wave_sleep", True)]:
        _kv_set(con, "phase7d_state", k, v)
    con.commit()
    return {"phase": PHASE, "cycle_index": cycle_index, "status": status, "slow_wave": sw,
            "safety": {"direct_fact_writes": "disabled", "direct_relation_writes": "disabled", "fact_promotion": "disabled", "no_word_blacklists": True, "slow_wave_sleep": True}}

def _run_downstream_cycle(self, progress):
    for mn in ("v8_phase7c_adaptive_boundaries_and_ei_balance_release", "v8_phase7b1_wake_chain_bridge_release",
               "v8_phase7b_endocannabinoid_retrograde_gain_control_release", "v8_phase7a_adenosine_homeostat_release",
               "v8_phase6d_saturation_homeostasis_and_meta_metaplasticity_release", "v8_phase6c_bias_persistence_and_self_regulating_meta_release",
               "v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release", "v8_phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release"):
        try:
            m = __import__("ki_system." + mn, fromlist=["managed_cycle"])
            if hasattr(m, "managed_cycle") and m.managed_cycle is not managed_cycle:
                return m.managed_cycle(self, progress), mn
        except Exception:
            continue
    return None, None

def managed_cycle(self, progress=None):
    downstream, dmod = _run_downstream_cycle(self, progress)
    try:
        db = resolve_db(self); p7d = run_phase7d_cycle(db)
    except Exception as exc:
        p7d = {"status": "phase7d_error", "error": str(exc), "phase": PHASE}
    return {"phase": PHASE, "downstream_module": dmod, "downstream_result": downstream, "phase7d_result": p7d}

def managed_run(self, cycles=1, progress=None):
    res = []
    try: cycles = int(cycles or 1)
    except Exception: cycles = 1
    for _ in range(max(1, cycles)): res.append(managed_cycle(self, progress))
    return {"phase": PHASE, "cycles": len(res), "results": res}

def autoload(AutonomousLoop):
    AutonomousLoop.cycle = managed_cycle; AutonomousLoop.run = managed_run
    AutonomousLoop.phase7d_slow_wave_sleep_substructure_release = True
    AutonomousLoop._phase7d_slow_wave_sleep_substructure_release = True
    AutonomousLoop.slow_wave_sleep = True
    for f in ("phase7c_adaptive_boundaries_and_ei_balance_release", "phase7b1_wake_chain_bridge_release",
              "phase7b_endocannabinoid_retrograde_gain_control_release", "phase7a_adenosine_homeostat_release",
              "phase6d_saturation_homeostasis_and_meta_metaplasticity_release", "phase6c_bias_persistence_and_self_regulating_meta_release",
              "phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release", "phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release",
              "no_word_blacklists", "adaptive_boundaries", "ei_balance", "sigmoid_soft_clipping", "adenosine_homeostat",
              "endocannabinoid_retrograde_gain_control", "wake_chain_bridge", "saturation_homeostasis", "meta_metaplasticity", "self_regulating_meta_parameters"):
        if not hasattr(AutonomousLoop, f): setattr(AutonomousLoop, f, True)
    AutonomousLoop.learning_mode = LEARNING_MODE; AutonomousLoop.fact_promotion = "disabled"
    AutonomousLoop.direct_fact_writes = "disabled"; AutonomousLoop.direct_relation_writes = "disabled"
    return AutonomousLoop
