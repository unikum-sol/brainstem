from __future__ import annotations
import re
import time
from collections import Counter
from ki_system import nlp
from ki_system.relation_quality import evaluate_relations
from ki_system.corpus_memory import ensure_corpus_schema, insert_candidate, upsert_language_pattern, upsert_negative_pattern, upsert_word_role
from ki_system.adaptive_quality import AdaptiveQuality
from ki_system.adaptive_alignment import AlignmentRoleLearner

FUNCTION_WORD_ROLES = {
    'und':'coordinator','oder':'coordinator','aber':'contrast_marker','jedoch':'contrast_marker',
    'der':'article','die':'article','das':'article','ein':'article','eine':'article',
    'ist':'copula','war':'copula','sind':'copula','wurde':'auxiliary','wurden':'auxiliary',
    'in':'preposition','auf':'preposition','von':'preposition','mit':'preposition','bei':'preposition',
    'seit':'temporal_marker','heute':'temporal_marker','anfang':'temporal_marker','mitte':'temporal_marker',
    'ende':'temporal_marker','ursprünglich':'temporal_marker','urspruenglich':'temporal_marker',
    'seitdem':'temporal_marker','mittlerweile':'temporal_marker','oft':'frequency_marker','zudem':'connector',
    'daher':'connector','deshalb':'connector','allerdings':'contrast_marker','was':'question_or_filler'
}
LICENSE_RE = re.compile(r'(creative commons|attribution-share alike|verfügbar unter|verfuegbar unter|wikimedia|wikipedia)', re.I)
DEFINITION_RE = re.compile(r'\b(ist|war)\s+(ein|eine|einer|eines|der|die|das)\b', re.I)
SOURCE_RE = re.compile(r'\b(einzelnachweise|literatur|weblinks|quelle|quellen|normdaten)\b', re.I)

class CorpusReader:
    def __init__(self, memory):
        self.memory = memory
        ensure_corpus_schema(memory)
        self.adaptive_quality = AdaptiveQuality(memory)
        self.alignment_roles = AlignmentRoleLearner(memory)
        self.stop_requested = False
        self.state = {'dopamine':0.42,'serotonin':0.65,'glutamate':0.35,'gaba':0.45,'noradrenaline':0.30,'acetylcholine':0.58}

    def stop(self):
        self.stop_requested = True

    def seed_reading_queue(self, limit=0):
        ensure_corpus_schema(self.memory)
        sql = """SELECT chunks.id, chunks.text, documents.title
                 FROM chunks JOIN documents ON documents.id=chunks.document_id
                 WHERE chunks.id NOT IN (SELECT chunk_id FROM reading_queue)"""
        params = ()
        if limit and int(limit) > 0:
            sql += " LIMIT ?"
            params = (int(limit),)
        rows = self.memory.rows(sql, params)
        now = int(time.time())
        added = 0
        with self.memory.lock:
            for row in rows:
                priority, reason, attention = self._initial_priority(row['text'] or '', row['title'] or '')
                self.memory.db.execute(
                    "INSERT OR IGNORE INTO reading_queue(chunk_id,priority,reason,attention_score,status,updated_at) VALUES(?,?,?,?,?,?)",
                    (row['id'], priority, reason, attention, 'pending', now),
                )
                added += 1
            self.memory.db.commit()
        return added

    def _initial_priority(self, text, title):
        if LICENSE_RE.search(text or ''):
            return 0.05, 'license_or_footer_signal', 0.05
        if SOURCE_RE.search((text or '')[:250]):
            return 0.10, 'source_section_signal', 0.08
        if DEFINITION_RE.search((text or '')[:700]):
            return 0.92, 'definition_signal', 0.90
        if title and title.lower().replace('_',' ') in (text or '')[:400].lower().replace('_',' '):
            return 0.72, 'title_intro_signal', 0.70
        return 0.35, 'raw_corpus', 0.35

    def _scores(self, text):
        text = text or ''
        fragment_score = 0.35 if len(text.strip()) < 120 else 0.0
        if text.count('\n') > 8 and len(text) < 900:
            fragment_score += 0.2
        return {
            'license_score': 0.95 if LICENSE_RE.search(text) else 0.0,
            'definition_score': 0.85 if DEFINITION_RE.search(text[:700]) else 0.15,
            'fragment_score': min(1.0, fragment_score),
            'source_score': 0.75 if SOURCE_RE.search(text[:300]) else 0.0,
        }

    def _learn_word_roles(self, text):
        for token in re.findall(r'[A-Za-zÄÖÜäöüß]+', (text or '').lower())[:220]:
            role = FUNCTION_WORD_ROLES.get(token)
            if role:
                upsert_word_role(self.memory, token, role, 0.9, (text or '')[:160])

    def _pattern(self, rel, reason=None):
        try:
            s, r, o = rel[:3]
        except Exception:
            return 'malformed_relation'
        return f"{reason}:{str(s)[:30]}->{str(o)[:30]}" if reason else f"{r}:{str(s)[:30]}->{str(o)[:30]}"

    def read_once(self, batch_size=50):
        ensure_corpus_schema(self.memory)
        # >>> SENSORY_DEPRIVATION_GUARD >>>
        try:
            from ki_system.v8_sensory_deprivation import is_deprivation_active as _sd_active
            if _sd_active(self.memory):
                return {"status": "sensory_deprivation_no_read", "seeded_reading_queue": 0, "totals": {}, "deprivation": True}
        except Exception:
            pass
        # <<< SENSORY_DEPRIVATION_GUARD <<<
        query = """SELECT rq.*, chunks.text, chunks.metadata_json, documents.title
                   FROM reading_queue rq
                   JOIN chunks ON chunks.id=rq.chunk_id
                   JOIN documents ON documents.id=chunks.document_id
                   WHERE rq.status='pending'
                   ORDER BY rq.priority DESC, rq.read_count ASC, rq.chunk_id ASC
                   LIMIT ?"""
        queue = self.memory.rows(query, (int(batch_size),))
        seeded = 0
        if not queue:
            seeded = self.seed_reading_queue(limit=2000)
            queue = self.memory.rows(query, (int(batch_size),))

        totals = Counter()
        rejected = Counter()
        adaptive_rejected = Counter()
        alignment_rejected = Counter()
        samples = []
        rejected_samples = []
        aligned = []
        now = int(time.time())

        for row in queue:
            if self.stop_requested:
                break
            chunk_id = row['chunk_id']
            text = row['text'] or ''
            ctx = row['title'] or ''
            scores = self._scores(text)
            self._learn_word_roles(text)
            try:
                ev = evaluate_relations(nlp.extract_relations(text, context_subject=ctx), context_subject=ctx)
            except Exception as exc:
                ev = {'raw_relations':0,'accepted_relations':0,'rejected_total':1,
                      'rejected_by_reason':{'reader_error':1},
                      'rejected_sample':[{'relation':[ctx,'error',str(exc)],'reason':'reader_error'}],
                      'aligned_subjects':0,'aligned_sample':[],'accepted':[]}

            totals['chunks_read'] += 1
            totals['raw_relations'] += ev.get('raw_relations', 0)
            totals['initial_accepted_relations'] += ev.get('accepted_relations', 0)
            totals['initial_rejected_relations'] += ev.get('rejected_total', 0)
            totals['aligned_subjects_from_quality_gate'] += ev.get('aligned_subjects', 0)
            rejected.update(ev.get('rejected_by_reason', {}))

            for item in ev.get('aligned_sample', [])[:5]:
                if len(aligned) < 10:
                    aligned.append(item)

            for s, r, o, c in ev.get('accepted', []):
                rel_scores = dict(scores)
                align_allowed, align_reason, align_score, role_details = self.alignment_roles.evaluate(s, r, o, ctx, text)
                rel_scores['alignment_score'] = max(float(rel_scores.get('alignment_score', 0.0) or 0.0), float(align_score))
                rel_scores['novelty_score'] = 0.5

                allowed, reason = self.adaptive_quality.classify_candidate(s, r, o, c, rel_scores)
                if allowed and not align_allowed:
                    allowed = False
                    reason = align_reason
                    alignment_rejected[align_reason] += 1
                self.adaptive_quality.observe(s, r, o, allowed, reason)
                self.alignment_roles.observe(s, allowed, reason, align_score, role_details)

                if allowed:
                    totals['accepted_relations'] += 1
                    if align_score >= float(self.alignment_roles.state.get('min_alignment_score', 0.18)):
                        totals['adaptive_aligned_subjects'] += 1
                    insert_candidate(self.memory, s, r, o, c, chunk_id, ctx, ctx, rel_scores, 'candidate')
                    upsert_language_pattern(self.memory, self._pattern((s, r, o)), 'accepted_relation', True, text[:200])
                    if len(samples) < 12:
                        samples.append({'accepted_candidate':[s, r, o], 'context':ctx, 'alignment_score':round(float(align_score),3), 'subject_role':role_details.get('subject_role')})
                else:
                    totals['adaptive_rejected_relations'] += 1
                    adaptive_rejected[reason] += 1
                    reject_scores = dict(rel_scores)
                    reject_scores['fragment_score'] = max(float(reject_scores.get('fragment_score', 0)), 0.7)
                    insert_candidate(self.memory, s, r, o, 0.0, chunk_id, ctx, ctx, reject_scores, 'rejected', reason)
                    upsert_negative_pattern(self.memory, self._pattern((s, r, o), reason), reason, text[:220])
                    upsert_language_pattern(self.memory, self._pattern((s, r, o), reason), 'adaptive_rejected_relation', False, text[:200])
                    if len(rejected_samples) < 12:
                        rejected_samples.append({'rejected_candidate':[s, r, o], 'reason': reason, 'alignment_score':round(float(align_score),3), 'subject_role':role_details.get('subject_role'), 'context': ctx})

            for rej in ev.get('rejected_sample', [])[:8]:
                reason = rej.get('reason', 'unknown')
                rel = rej.get('relation', ['', '', ''])
                try:
                    s, r, o = rel[:3]
                except Exception:
                    s, r, o = ctx, 'unknown', str(rel)
                rel_scores = dict(scores)
                align_allowed, align_reason, align_score, role_details = self.alignment_roles.evaluate(s, r, o, ctx, text)
                rel_scores['alignment_score'] = max(float(rel_scores.get('alignment_score', 0.0) or 0.0), float(align_score))
                rel_scores['fragment_score'] = max(rel_scores.get('fragment_score', 0), 0.7)
                if 'license' in reason:
                    rel_scores['license_score'] = 1.0
                self.adaptive_quality.observe(s, r, o, False, reason)
                self.alignment_roles.observe(s, False, reason, align_score, role_details)
                insert_candidate(self.memory, s, r, o, 0.0, chunk_id, ctx, ctx, rel_scores, 'rejected', reason)
                upsert_negative_pattern(self.memory, self._pattern(rel, reason), reason, text[:220])
                upsert_language_pattern(self.memory, self._pattern(rel, reason), 'rejected_relation', False, text[:200])

            with self.memory.lock:
                status = 'read_candidate' if ev.get('accepted_relations', 0) else 'read_no_candidate'
                self.memory.db.execute(
                    "UPDATE reading_queue SET read_count=read_count+1,status=?,last_read=?,updated_at=? WHERE chunk_id=?",
                    (status, now, now, chunk_id),
                )
                self.memory.db.commit()

        sleep_quality = self.adaptive_quality.sleep_consolidate()
        sleep_alignment = self.alignment_roles.consolidate()
        return {
            'status':'adaptive_alignment_corpus_reader_phase3d6j',
            'seeded_reading_queue':seeded,
            'totals':dict(totals),
            'rejected_by_reason':dict(rejected),
            'adaptive_rejected_by_reason':dict(adaptive_rejected),
            'alignment_rejected_by_reason':dict(alignment_rejected),
            'aligned_samples':aligned,
            'samples':samples,
            'adaptive_rejected_samples':rejected_samples,
            'promoted_to_facts':0,
            'direct_fact_writes':'disabled',
            'direct_relation_writes':'disabled',
            'adaptive_quality':self.adaptive_quality.summary(),
            'alignment_role_learning':self.alignment_roles.summary(),
            'sleep_consolidation':{'quality':sleep_quality, 'alignment':sleep_alignment},
        }


# PHASE3D6K_CANDIDATE_SLEEP_PRUNING
# Adds sleep-time candidate pruning after each safe corpus-reader pass.
try:
    from ki_system.candidate_sleep_pruning import apply_patch as _p3d6k_apply_candidate_sleep_pruning
    _p3d6k_apply_candidate_sleep_pruning(CorpusReader)
except Exception:
    pass


# PHASE3D6L_RELATION_REPAIR_AND_CANDIDATE_TYPING
# Adds candidate typing and relation repair after safe reader/pruning. No facts/relations promotion.
try:
    from ki_system.relation_repair import apply_patch as _p3d6l_apply_relation_repair
    _p3d6l_apply_relation_repair(CorpusReader)
except Exception:
    pass


# PHASE3D6L1_RELATION_REPAIR_SAFETY_FIX
# Safer relation repair with rollback for unsafe repaired candidates. No facts/relations promotion.
try:
    from ki_system.relation_repair import apply_patch as _p3d6l1_apply_relation_repair
    _p3d6l1_apply_relation_repair(CorpusReader)
except Exception:
    pass


# PHASE3D6L2_DEFINITION_CANDIDATE_GUARD
# Guards definition_candidate rows after relation repair. No facts/relations promotion.
try:
    from ki_system.definition_candidate_guard import apply_patch as _p3d6l2_apply_definition_candidate_guard
    _p3d6l2_apply_definition_candidate_guard(CorpusReader)
except Exception:
    pass


# PHASE3D6M_CANDIDATE_ACCEPTANCE_TIGHTENING
# Tightens candidate acceptance before storing candidates. No facts/relations promotion.
try:
    from ki_system.candidate_acceptance_tightening import apply_patch as _p3d6m_apply_candidate_acceptance_tightening
    from ki_system.adaptive_quality import AdaptiveQuality as _p3d6m_AdaptiveQuality
    _p3d6m_apply_candidate_acceptance_tightening(_p3d6m_AdaptiveQuality)
except Exception:
    pass


# PHASE3D6N_PREDICATE_QUALITY_AND_ADJECTIVE_GATE
# Blocks predicate/adjective-like is_a candidates before storing. No facts/relations promotion.
try:
    from ki_system.predicate_quality_gate import apply_patch as _p3d6n_apply_predicate_quality_gate
    from ki_system.adaptive_quality import AdaptiveQuality as _p3d6n_AdaptiveQuality
    _p3d6n_apply_predicate_quality_gate(_p3d6n_AdaptiveQuality)
except Exception:
    pass


# PHASE3D6O_HEADING_ARTIFACT_AND_CLAUSE_GATE
# Blocks heading-artifact and clause-frame candidates before storing. No facts/relations promotion.
try:
    from ki_system.heading_artifact_clause_gate import apply_patch as _p3d6o_apply_heading_clause_gate
    from ki_system.adaptive_quality import AdaptiveQuality as _p3d6o_AdaptiveQuality
    _p3d6o_apply_heading_clause_gate(_p3d6o_AdaptiveQuality)
except Exception:
    pass


# PHASE3D6P_STATUS_LABEL_AND_PATCH_ORDER_FIX
# Final observability patch: enforces deterministic gate setup and status label phase3d6p.
try:
    from ki_system.phase3d6p_patch_order_status import install as _p3d6p_install_patch_order_status
    _p3d6p_install_patch_order_status(CorpusReader)
except Exception:
    pass


# PHASE3D7_CANDIDATE_QUALITY_CONSOLIDATION_PACK
# Consolidates 3d6m/n/o gates and final status label. No facts/relations promotion.
try:
    from ki_system.candidate_quality_consolidation import install_reader_status as _p3d7_install_quality_pack
    _p3d7_install_quality_pack(CorpusReader)
except Exception:
    pass


# PHASE3D8_CANDIDATE_TYPE_REFINEMENT_PACK
# Types candidate rows into definition/property/relation/needs_review buckets. No facts/relations promotion.
try:
    from ki_system.candidate_type_refinement import install_reader as _p3d8_install_candidate_type_refinement
    _p3d8_install_candidate_type_refinement(CorpusReader)
except Exception:
    pass
