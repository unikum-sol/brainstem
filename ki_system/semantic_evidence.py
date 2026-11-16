"""Evidence-typed surface validation and unverified text contrast discovery.

No language-specific words, negation lists, pretrained model or generated grammar.
A surface contrast is NOT a logical contradiction. Repetition is NOT truth.
"""
from ki_system import learning_clock as _learning_clock
import difflib
import json
import math
import re
import unicodedata
import time

SCHEMA_TABLES = {
    'semantic_evidence_state': [('key','TEXT PRIMARY KEY'),('value','TEXT'),('updated_at','INTEGER')],
    'semantic_text_contrasts': [
        ('pair_key','TEXT PRIMARY KEY'),('hypothesis_a','INTEGER'),('hypothesis_b','INTEGER'),
        ('contradiction_id','INTEGER'),('gap_id','INTEGER'),('similarity','REAL'),
        ('anchors_json','TEXT'),('differences_json','TEXT'),('evidence_a','INTEGER'),
        ('evidence_b','INTEGER'),('status',"TEXT DEFAULT 'unverified'"),
        ('created_at','INTEGER'),('updated_at','INTEGER'),
        ('kind','TEXT'),('frame_id','INTEGER'),
    ],
    # A frame is the shared token sequence of two aligned observations with
    # each differing span replaced by a slot; its fillers are the spans seen
    # in the slots. Advisory council of 16 November 2026.
    'semantic_text_frames': [
        ('frame_id','INTEGER PRIMARY KEY'),('signature','TEXT'),('n_slots','INTEGER'),
        ('n_pairs','INTEGER DEFAULT 0'),('n_fillers','INTEGER DEFAULT 0'),
        ('n_sources','INTEGER DEFAULT 0'),('anchor_min_df','INTEGER'),
        ('slot_status','TEXT'),('slot_fillers_json','TEXT'),('gap_id','INTEGER'),('first_cycle','INTEGER'),
        ('last_cycle','INTEGER'),('created_at','INTEGER'),('updated_at','INTEGER'),
    ],
    'semantic_frame_fillers': [
        ('id','INTEGER PRIMARY KEY'),('frame_id','INTEGER'),('slot','INTEGER'),
        ('filler','TEXT'),('n','INTEGER DEFAULT 0'),
    ],
    'semantic_frame_sources': [
        ('id','INTEGER PRIMARY KEY'),('frame_id','INTEGER'),('title','TEXT'),
    ],
    # Every gap status this module changes, so the change can be undone:
    # UPDATE internal_learning_gaps SET status=prev_status WHERE id=gap_id.
    'semantic_frame_gap_log': [
        ('id','INTEGER PRIMARY KEY'),('gap_id','INTEGER'),('frame_id','INTEGER'),
        ('prev_status','TEXT'),('new_status','TEXT'),('reason','TEXT'),('created_at','INTEGER'),
    ],
}
UNIQUE_INDEXES = [
    ('idx_semantic_frames_signature', 'semantic_text_frames', ('signature',)),
    ('idx_semantic_frame_fillers_key', 'semantic_frame_fillers', ('frame_id', 'slot', 'filler')),
    ('idx_semantic_frame_sources_key', 'semantic_frame_sources', ('frame_id', 'title')),
]
DEFAULTS = {'index_checkpoint':'0','scan_checkpoint':'0','scan_batch':'32',
            'peer_limit':'16','min_similarity':'0.65','min_shared_tokens':'3',
            'contrasts_created_total':'0',
            # Retrieval: cue terms in rising document frequency while their
            # summed postings stay within a budget of match_budget_fraction of
            # the index; at most candidate_limit peers aligned per observation.
            'match_budget_fraction':'0.025','match_budget_min':'1024','candidate_limit':'64',
            # A slot with at most this many distinct fillers is closed (one
            # value per subject); from paradigmatic_min_fillers on it is an
            # open slot class (Gomez 2002: frames are found at 24 fillers).
            'closed_slot_max_fillers':'3','paradigmatic_min_fillers':'24',
            'backfill_checkpoint':'0','backfill_batch':'500',
            'frames_created_total':'0','frame_pairs_total':'0',
            'observations_skipped_total':'0','gaps_superseded_total':'0'}


def _columns(con,table):
    return {r[1] for r in con.execute('PRAGMA table_info('+table+')')}


def _self_check_schema(con):
    missing=[table+'.'+name for table,cols in SCHEMA_TABLES.items()
             for name,spec in cols if name not in _columns(con,table)]
    for table in ('relations','ontology'):
        missing += [table+'.'+name for name in ('evidence_kind','semantic_status')
                    if name not in _columns(con,table)]
    fts = con.execute("SELECT sql FROM sqlite_master WHERE name='semantic_observation_fts'").fetchone()
    if not fts or 'using fts5' not in (fts[0] or '').lower():
        missing.append('semantic_observation_fts: expected FTS5 virtual table')
    return missing


def ensure_schema(con):
    # Standalone schema/migration checks also use the canonical bootstrap DDL.
    from ki_system.db_bootstrap import SCHEMA_TABLES as central
    for core in ('relations','ontology','context_hypotheses'):
        if not _columns(con,core):
            con.execute('CREATE TABLE IF NOT EXISTS '+core+' ('+
                        ', '.join(name+' '+spec for name,spec in central[core])+')')
    for table,cols in SCHEMA_TABLES.items():
        con.execute('CREATE TABLE IF NOT EXISTS '+table+' ('+', '.join(n+' '+s for n,s in cols)+')')
        have=_columns(con,table)
        for name,spec in cols:
            if name not in have:
                con.execute('ALTER TABLE '+table+' ADD COLUMN '+name+' '+spec)
    for table in ('relations','ontology'):
        if not _columns(con,table):
            raise RuntimeError('Bootstrap must create '+table+' before semantic evidence schema')
        for name in ('evidence_kind','semantic_status'):
            if name not in _columns(con,table):
                con.execute('ALTER TABLE '+table+' ADD COLUMN '+name+" TEXT DEFAULT 'legacy_unverified'")
    con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS semantic_observation_fts USING fts5(text, tokenize='unicode61')")
    con.execute('CREATE INDEX IF NOT EXISTS idx_semantic_hypothesis_role_id ON context_hypotheses(role,id)')
    con.execute('CREATE INDEX IF NOT EXISTS idx_semantic_contrast_hypotheses ON semantic_text_contrasts(hypothesis_a,hypothesis_b)')
    con.execute('CREATE INDEX IF NOT EXISTS idx_semantic_contrast_gap ON semantic_text_contrasts(gap_id)')
    for name, table, cols in UNIQUE_INDEXES:
        con.execute('CREATE UNIQUE INDEX IF NOT EXISTS ' + name + ' ON ' + table + '(' + ','.join(cols) + ')')
    if _columns(con,'stageb_graduation_events'):
        con.execute('CREATE INDEX IF NOT EXISTS idx_semantic_graduation_hypothesis ON stageb_graduation_events(hypothesis_id,id)')
    now=_learning_clock.now()
    for k,v in DEFAULTS.items():
        con.execute('INSERT OR IGNORE INTO semantic_evidence_state(key,value,updated_at) VALUES(?,?,?)',(k,v,now))
    missing=_self_check_schema(con)
    if missing:raise RuntimeError('Semantic evidence schema missing: '+repr(missing))
    con.commit()


def _read_kv(con,table):
    return dict(con.execute('SELECT key,value FROM '+table).fetchall())


def _set(con,key,value):
    con.execute('INSERT INTO semantic_evidence_state(key,value,updated_at) VALUES(?,?,?) '
                'ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at',
                (key,str(value),_learning_clock.now()))


def _word_char(char):
    return char.isalnum() or char=='_'


def surface_supported(text,surface):
    """Structural source-span evidence only, never a semantic truth score.

    Whitespace/punctuation edges are observed delimiters, not a word blacklist.
    Multiword spans are allowed. Unsegmented learned spans remain hypotheses.
    """
    text=' '.join((text or '').split()).casefold()
    surface=' '.join((surface or '').split()).casefold()
    if not surface:return False
    start=0
    while True:
        pos=text.find(surface,start)
        if pos<0:return False
        end=pos+len(surface)
        if (pos==0 or not _word_char(text[pos-1])) and (end==len(text) or not _word_char(text[end])):
            return True
        start=pos+1


def relation_surface_evidence(con,chunk_id,source,target):
    row=con.execute('SELECT text FROM chunks WHERE id=?',(chunk_id,)).fetchone()
    if row and surface_supported(row[0],source) and surface_supported(row[0],target):
        return 'observed_delimited_spans'
    if not row:
        return None
    source_text=' '.join((row[0] or '').split()).casefold()
    if not all(' '.join((span or '').split()).casefold() in source_text for span in (source,target)):
        return None
    # A learned span in unsegmented text can be corroborated by independent
    # delimited occurrences elsewhere in the actual corpus. Bounded FTS lookup.
    if not con.execute("SELECT 1 FROM sqlite_master WHERE name='chunks_fts'").fetchone():
        return None
    for span in (source,target):
        if surface_supported(row[0],span):
            continue
        terms=re.findall(r'\w+',span,flags=re.UNICODE)
        if not terms:return None
        query='"'+' '.join(terms).replace('"','""')+'"'
        peers=con.execute("SELECT c.id,c.text FROM chunks_fts JOIN chunks c ON c.id=chunks_fts.rowid "
                          "WHERE chunks_fts MATCH ? AND c.id<>? ORDER BY bm25(chunks_fts),c.id LIMIT 8",
                          (query,chunk_id)).fetchall()
        if not any(surface_supported(text,span) for cid,text in peers):
            return None
    return 'cross_chunk_delimiter_corroboration'


def text_contrast(a,b,min_similarity=.65,min_shared=3):
    """Ordered alignment, no interpretation of polarity or exclusivity."""
    ta=re.findall(r'\w+',a.casefold(),flags=re.UNICODE)
    tb=re.findall(r'\w+',b.casefold(),flags=re.UNICODE)
    if not ta or ta==tb:return None
    matcher=difflib.SequenceMatcher(None,ta,tb,autojunk=False)
    similarity=matcher.ratio()
    anchors=[];differences=[];shared=0
    for tag,i,j,k,l in matcher.get_opcodes():
        if tag=='equal':
            shared+=j-i;anchors.append({'tokens':ta[i:j],'a':[i,j],'b':[k,l]})
        else:
            differences.append({'operation':tag,'a':ta[i:j],'b':tb[k:l],
                                'a_span':[i,j],'b_span':[k,l]})
    if shared<min_shared or similarity<min_similarity:return None
    return {'similarity':similarity,'anchors':anchors,'differences':differences,
            'semantic_verdict':'unverified','shared_tokens':shared}


def _observation_rows(con,checkpoint,limit):
    return con.execute("SELECT id,text_excerpt FROM context_hypotheses WHERE id>? "
                       "AND role IN ('uncertain_hypothesis','stable_hypothesis') "
                       "AND lexical_offset IS NULL AND COALESCE(relation_hint,'')='' "
                       "AND COALESCE(object,'')='' AND COALESCE(status,'active')='active' "
                       "AND text_excerpt IS NOT NULL ORDER BY id LIMIT ?",(checkpoint,limit)).fetchall()


def _fold(term):
    return ''.join(c for c in unicodedata.normalize('NFKD', term) if not unicodedata.combining(c))


def _term_df(con, terms):
    """Document frequency of each term in the observation index."""
    con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS temp.semantic_observation_vocab "
                "USING fts5vocab(main, semantic_observation_fts, 'row')")
    folded = {t: _fold(t) for t in terms}
    keys = sorted(set(folded.values()))
    if not keys:
        return {}
    df = dict(con.execute("SELECT term, doc FROM temp.semantic_observation_vocab WHERE term IN (" +
                          ",".join("?" for _ in keys) + ")", keys).fetchall())
    return {t: int(df.get(folded[t], 0)) for t in terms}


def _rarest_terms(con, terms, k):
    """The k terms of an observation that occur in the fewest indexed
    observations (inverse document frequency); rare shared words identify
    aligned alternatives better than frequent ones and keep the full-text
    search cheap as the index grows. Literatur: Spärck Jones 1972"""
    if len(terms) <= k:
        return terms
    df = _term_df(con, terms)
    order = sorted(range(len(terms)), key=lambda i: (df[terms[i]], i))
    return [terms[i] for i in sorted(order[:k])]


def _cue_terms(terms, df, min_similarity, budget):
    """Sparse, specific retrieval cues (pattern separation in the dentate
    gyrus and pattern completion from a partial cue in CA3: Marr 1971;
    Treves & Rolls 1994; Yassa & Stark 2011; the index holds pointers, not
    copies: Teyler & DiScenna 1986).

    A peer whose alignment ratio reaches s shares at least s/(2-s) of this
    observation's tokens, so it contains one of its p rarest tokens with
    p = n - ceil(s/(2-s) n) + 1 (prefix filtering: Bayardo, Ma & Srikant
    2007; Xiao et al. 2008). Terms are taken in rising document frequency
    while their summed postings stay within the budget (frequent terms are
    never enumerated: Turtle & Flood 1995; Broder et al. 2003). An
    observation whose rarest term already exceeds the budget consists of
    frequent material only and gives no specific cue."""
    position = {t: i for i, t in enumerate(terms)}
    order = sorted(terms, key=lambda t: (df.get(t, 0), position[t]))
    n = len(order)
    p = max(1, n - math.ceil(min_similarity / (2.0 - min_similarity) * n) + 1)
    cues, total = [], 0
    for t in order[:p]:
        if total + df.get(t, 0) > budget:
            break
        cues.append(t)
        total += df.get(t, 0)
    return cues


def _candidates(con, hid, cues, limit):
    """Peers that share the specific cues, ranked by bm25 over the cues only.
    The budget bounds the matches bm25 has to score; before, a query of six
    frequent terms could match 75,708 observations. Offline replay on 3,200
    observations of the production state (16 November 2026): ranking the
    bounded matches by bm25 found 98.4 % of the earlier pairs with a
    specific anchor, ranking by the number of shared cues only 85 %."""
    query = ' OR '.join('"' + t.replace('"', '""') + '"' for t in cues)
    return [r[0] for r in con.execute('SELECT rowid FROM semantic_observation_fts WHERE semantic_observation_fts MATCH ? '
                                      'AND rowid<>? ORDER BY bm25(semantic_observation_fts),rowid LIMIT ?',
                                      (query, hid, limit))]


def _frame_of(alignment):
    """Signature and slot fillers of an aligned pair: the shared tokens in
    order, each differing span replaced by one slot (minimal pairs and the
    substitution test: Harris 1954; Cartwright & Brent 1997; van Zaanen
    2000). Works on the stored anchors and differences, so existing
    contrasts can be framed again without re-reading their texts."""
    parts = [(a['a'][0], a['b'][0], 1, a['tokens']) for a in alignment['anchors']]
    parts += [(d['a_span'][0], d['b_span'][0], 0, (d['a'], d['b'])) for d in alignment['differences']]
    sig, fillers, anchors = [], [], []
    for _, _, is_anchor, value in sorted(parts, key=lambda x: (x[0], x[1], x[2])):
        if is_anchor:
            sig.extend(value)
            anchors.extend(value)
        else:
            sig.append('<_>')
            fillers.append((' '.join(value[0]), ' '.join(value[1])))
    return ' '.join(sig), fillers, anchors


def _index_size(con, state):
    n = int(state.get('indexed_total', 0) or 0)
    if n <= 0:
        n = con.execute('SELECT COUNT(*) FROM semantic_observation_fts').fetchone()[0]
    return max(1, n)


def _log_gap_status(con, gap_id, frame_id, new_status, reason, now):
    row = con.execute('SELECT status FROM internal_learning_gaps WHERE id=?', (gap_id,)).fetchone()
    if row is None or row[0] in ('closed', 'resolved', new_status):
        return False
    con.execute('INSERT INTO semantic_frame_gap_log(gap_id,frame_id,prev_status,new_status,reason,created_at) '
                'VALUES(?,?,?,?,?,?)', (gap_id, frame_id, row[0], new_status, reason, now))
    con.execute('UPDATE internal_learning_gaps SET status=?, habituated_at=?, updated_at=? WHERE id=?',
                (new_status, now, now, gap_id))
    return True


def _record_frame(con, signature, fillers, anchors, df, titles, cycle, now):
    """Count the pair in its frame; filler and source counts are kept
    incrementally. Returns (frame_id, n_fillers, anchor_min_df, created)."""
    row = con.execute('SELECT frame_id, anchor_min_df, slot_fillers_json, n_sources FROM semantic_text_frames '
                      'WHERE signature=?', (signature,)).fetchone()
    created = row is None
    if created:
        amin = min((df.get(t, 0) for t in anchors), default=0)
        fid = con.execute('INSERT INTO semantic_text_frames(signature,n_slots,n_pairs,n_fillers,n_sources,anchor_min_df,'
                          'slot_fillers_json,first_cycle,last_cycle,created_at,updated_at) VALUES(?,?,0,0,0,?,?,?,?,?,?)',
                          (signature, len(fillers), amin, json.dumps([0] * len(fillers)), cycle, cycle, now, now)).lastrowid
        per_slot, n_src = [0] * len(fillers), 0
    else:
        fid, amin, per_slot_json, n_src = row
        per_slot = json.loads(per_slot_json or '[]')
        per_slot += [0] * (len(fillers) - len(per_slot))
    for slot, pair in enumerate(fillers):
        for filler in sorted(set(pair)):
            if con.execute('INSERT OR IGNORE INTO semantic_frame_fillers(frame_id,slot,filler,n) VALUES(?,?,?,1)',
                           (fid, slot, filler)).rowcount:
                per_slot[slot] += 1
            else:
                con.execute('UPDATE semantic_frame_fillers SET n=n+1 WHERE frame_id=? AND slot=? AND filler=?',
                            (fid, slot, filler))
    for title in sorted({t for t in titles if t}):
        n_src += con.execute('INSERT OR IGNORE INTO semantic_frame_sources(frame_id,title) VALUES(?,?)',
                             (fid, title)).rowcount
    n_fill = max(per_slot, default=0)
    con.execute('UPDATE semantic_text_frames SET n_pairs=n_pairs+1, n_fillers=?, n_sources=?, slot_fillers_json=?, '
                'last_cycle=?, updated_at=? WHERE frame_id=?', (n_fill, n_src, json.dumps(per_slot), cycle, now, fid))
    return fid, n_fill, amin, created


def _slot_status(n_fill, state):
    if n_fill <= int(state['closed_slot_max_fillers']):
        return 'closed_slot'
    if n_fill >= int(state['paradigmatic_min_fillers']):
        return 'paradigmatic'
    return 'undecided'


def _classify_pair(con, key, a, b, alignment, obs, df, n_index, state, ctx, cid=None):
    """Route an aligned pair (advisory council of 16 November 2026).

    Two observations that differ in one aligned span are first a mismatch
    signal of the hippocampal comparator, not a contradiction (Kumaran &
    Maguire 2007; Duncan et al. 2012). Many fillers in one frame are
    paradigmatic evidence, a substitution class (Harris 1954; Mintz 2003;
    Gomez 2002); they are collected per frame and never become a gap. Only a
    variant that is incongruent with a consolidated memory gets privileged
    processing (van Kesteren et al. 2012; Lisman & Grace 2005): it becomes a
    contradiction and one gap per frame, if one side is stable, the frame
    names a specific subject (an anchor rarer than sqrt(N) observations),
    the slot is still closed (one value per subject, Yang 2016) and the two
    observations come from different articles."""
    ra, rb = obs
    titles = (ra[5], rb[5])
    signature, fillers, anchors = _frame_of(alignment)
    fid, n_fill, amin, created = _record_frame(con, signature, fillers, anchors, df, titles, ctx['cycle'], ctx['now'])
    ctx['frames_created'] += int(created)
    ctx['frame_pairs'] += 1
    status = _slot_status(n_fill, state)
    stable = 'stable_hypothesis' in (ra[6], rb[6])
    distinct_sources = bool(titles[0]) and bool(titles[1]) and titles[0] != titles[1]
    is_contrast = stable and amin <= math.sqrt(n_index) and status == 'closed_slot' and distinct_sources
    frame_gap = con.execute('SELECT gap_id FROM semantic_text_frames WHERE frame_id=?', (fid,)).fetchone()[0]
    old = con.execute('SELECT gap_id FROM semantic_text_contrasts WHERE pair_key=?', (key,)).fetchone()
    pair_gap = old[0] if old else None
    gid = None
    if is_contrast:
        details = {'evidence_kind': 'ordered_surface_contrast', 'semantic_status': 'unverified',
                   'hypothesis_ids': [a, b], 'source_chunk_ids': [ra[3], rb[3]],
                   'observed_texts': [ra[1], rb[1]], 'alignment': alignment, 'frame_id': fid,
                   'no_automatic_resolution': True, 'repetition_is_not_truth': True}
        payload = json.dumps(details, ensure_ascii=False, sort_keys=True)
        if cid:
            # Never promote an unverified contrast to resolvable by frequency.
            con.execute("UPDATE contradictions SET details_json=?,value_a=?,value_b=? WHERE id=? "
                        "AND relation='unverified_text_contrast' AND status='unverified'", (payload, ra[1], rb[1], cid))
        else:
            cid = con.execute('INSERT INTO contradictions(subject,relation,value_a,value_b,status,details_json,created_at) '
                              "VALUES(?,'unverified_text_contrast',?,?,'unverified',?,?)",
                              ('contrast:' + key, ra[1], rb[1], payload, ctx['now'])).lastrowid
            ctx['created'] += 1
        # One gap per frame; reuses the gap -> question -> chunk feedback.
        gapkey = 'semantic_frame:' + str(fid)
        ctx['upsert_gap'](con, gapkey, 'unverified_text_contrast',
                          'Observed aligned alternatives; incompatibility and scope are not learned',
                          'uncertain_hypothesis', .5 + .3 * alignment['similarity'], .5, a,
                          float(ra[4] if ra[4] is not None else 1.), ra[1], int(ra[2] or 0) + int(rb[2] or 0),
                          ctx['now'], habituation_max=ctx['habituation_max'])
        gid = con.execute('SELECT id FROM internal_learning_gaps WHERE gap_key=?', (gapkey,)).fetchone()[0]
        con.execute('UPDATE semantic_text_frames SET gap_id=?, slot_status=? WHERE frame_id=?', (gid, status, fid))
    else:
        con.execute('UPDATE semantic_text_frames SET slot_status=? WHERE frame_id=?', (status, fid))
        if frame_gap and status != 'closed_slot':
            # The slot has opened into a substitution class: the frame's gap
            # habituates (repetition suppression is stimulus-specific:
            # Grill-Spector, Henson & Martin 2006; Rankin et al. 2009).
            if _log_gap_status(con, frame_gap, fid, 'habituated', 'frame_slot_opened', ctx['now']):
                ctx['superseded'] += 1
    kind = 'contrast' if is_contrast else 'frame'
    if kind == 'frame' and pair_gap and pair_gap != frame_gap:
        # The per-pair gap of a pair stored before the frame rule.
        if _log_gap_status(con, pair_gap, fid, 'habituated', 'pair_reclassified_as_frame', ctx['now']):
            ctx['superseded'] += 1
    con.execute('INSERT INTO semantic_text_contrasts(pair_key,hypothesis_a,hypothesis_b,contradiction_id,gap_id,similarity,'
                'anchors_json,differences_json,evidence_a,evidence_b,status,created_at,updated_at,kind,frame_id) '
                "VALUES(?,?,?,?,?,?,?,?,?,?,'unverified',?,?,?,?) ON CONFLICT(pair_key) DO UPDATE SET "
                'contradiction_id=COALESCE(semantic_text_contrasts.contradiction_id,excluded.contradiction_id),'
                'gap_id=COALESCE(semantic_text_contrasts.gap_id,excluded.gap_id),'
                'similarity=excluded.similarity,anchors_json=excluded.anchors_json,differences_json=excluded.differences_json,'
                'evidence_a=excluded.evidence_a,evidence_b=excluded.evidence_b,updated_at=excluded.updated_at,'
                'kind=excluded.kind,frame_id=excluded.frame_id',
                (key, a, b, cid if is_contrast else None, gid, alignment['similarity'],
                 json.dumps(alignment['anchors'], ensure_ascii=False),
                 json.dumps(alignment['differences'], ensure_ascii=False), ra[2], rb[2], ctx['now'], ctx['now'], kind, fid))
    return kind


# The article of an observation comes from its chunk (source_title is not
# filled on the production state).
_OBS_SQL = ("SELECT h.id,h.text_excerpt,h.evidence_count,h.chunk_id,h.uncertainty,"
            "COALESCE(NULLIF(h.source_title,''),json_extract(ch.metadata_json,'$.article')),h.role "
            "FROM context_hypotheses h LEFT JOIN chunks ch ON ch.id=h.chunk_id "
            "WHERE h.id IN ({}) AND h.role IN ('uncertain_hypothesis','stable_hypothesis') "
            "AND COALESCE(h.status,'active')='active'")


def _backfill_frames(con, state, ctx, n_index):
    """Frame the contrasts stored before 16 November 2026, a bounded batch
    per cycle, from their stored alignments (offline reprocessing that
    extracts the gist: Lewis & Durrant 2011). Contradiction rows stay as
    they are; the open per-pair gap of a pair that is no contrast under the
    frame rule habituates, with its previous status logged."""
    ckpt = int(state['backfill_checkpoint'])
    if ckpt < 0:
        return 0
    batch = max(1, int(state['backfill_batch']))
    cols = ('c.rowid,c.pair_key,c.hypothesis_a,c.hypothesis_b,c.gap_id,c.similarity,c.anchors_json,'
            'c.differences_json,c.contradiction_id,c.frame_id')
    # Pairs whose gap is still active come first: they steer the strategy
    # phases now. The checkpoint stays where it is for this pass.
    rows = con.execute('SELECT ' + cols + ' FROM internal_learning_gaps g JOIN semantic_text_contrasts c ON c.gap_id=g.id '
                       "WHERE COALESCE(g.status,'open') NOT IN ('closed','resolved','habituated') "
                       "AND g.gap_type='unverified_text_contrast' AND c.frame_id IS NULL LIMIT ?", (batch,)).fetchall()
    keep_ckpt = bool(rows)
    if not rows:
        rows = con.execute('SELECT ' + cols + ' FROM semantic_text_contrasts c WHERE c.rowid>? ORDER BY c.rowid LIMIT ?',
                           (ckpt, batch)).fetchall()
    if not rows:
        _set(con, 'backfill_checkpoint', -1)
        return 0
    done = 0
    for rowid, key, a, b, pair_gap, sim, anchors_json, diff_json, cid, frame_id in rows:
        if not keep_ckpt:
            ckpt = rowid
        if frame_id is not None:
            continue
        alignment = {'anchors': json.loads(anchors_json or '[]'), 'differences': json.loads(diff_json or '[]'),
                     'similarity': float(sim or 0)}
        signature, fillers, anchors = _frame_of(alignment)
        df = _term_df(con, list(dict.fromkeys(anchors)))
        obs = {r[0]: r for r in con.execute(_OBS_SQL.format('?,?'), (a, b))}
        if len(obs) == 2:
            _classify_pair(con, key, a, b, alignment, (obs[a], obs[b]), df, n_index, state, ctx, cid=cid)
        else:
            # A side was revised or retired: count the frame, nothing else.
            fid = _record_frame(con, signature, fillers, anchors, df, (), ctx['cycle'], ctx['now'])[0]
            ctx['frame_pairs'] += 1
            con.execute("UPDATE semantic_text_contrasts SET kind='frame', frame_id=? WHERE rowid=?", (fid, rowid))
            if pair_gap and _log_gap_status(con, pair_gap, fid, 'habituated', 'pair_reclassified_as_frame', ctx['now']):
                ctx['superseded'] += 1
        done += 1
    _set(con, 'backfill_checkpoint', ckpt)
    return done


def discover_text_contrasts(con):
    ensure_schema(con)
    from ki_system.v8_stageb_gap_detection_release import (_upsert_gap, _neuromodulators, _current_cycle,
        STATE_TABLE as GAP_STATE, ensure_schema as ensure_gap_schema)
    ensure_gap_schema(con)
    gap_state = _read_kv(con, GAP_STATE)
    serotonin = _neuromodulators(con)['serotonin']
    habituation_max = max(1, round(float(gap_state.get('habituation_max_stagnant_cycles',64)) *
        (1.0 + float(gap_state.get('selection_pressure_serotonin_gain',0.5)) * (serotonin - 0.5))))
    state=_read_kv(con,'semantic_evidence_state')
    for k, v in DEFAULTS.items():
        state.setdefault(k, v)
    batch=min(128,max(1,int(state['scan_batch'])))
    limit=min(256,max(1,int(state['candidate_limit'])))
    min_sim=float(state['min_similarity']); min_shared=int(state['min_shared_tokens'])
    checkpoint=int(state['index_checkpoint']);fresh=_observation_rows(con,checkpoint,batch)
    n_index = _index_size(con, state)
    # Postings budget relative to the index, so it scales with the corpus.
    budget=max(int(float(state['match_budget_min'])),int(float(state['match_budget_fraction'])*n_index))
    for hid,text in fresh:
        if not con.execute('SELECT 1 FROM semantic_observation_fts WHERE rowid=?',(hid,)).fetchone():
            con.execute('INSERT INTO semantic_observation_fts(rowid,text) VALUES(?,?)',(hid,text))
            n_index += 1
        checkpoint=hid
    _set(con,'index_checkpoint',checkpoint)
    _set(con,'indexed_total',n_index)
    now=_learning_clock.now()
    ctx = {'cycle': _current_cycle(con), 'now': now, 'created': 0, 'frames_created': 0, 'frame_pairs': 0,
           'superseded': 0, 'upsert_gap': _upsert_gap, 'habituation_max': habituation_max}
    # Rotate the scan so old candidates can receive real new evidence. No
    # unbounded all-pairs scan and no manual subject merging.
    scan=int(state['scan_checkpoint']);rows=_observation_rows(con,scan,batch)
    if not rows:scan=0;rows=_observation_rows(con,0,batch)
    examined=0;skipped=0;contrasts=0;seen=set()
    for hid,text in rows:
        scan=hid
        terms=list(dict.fromkeys(re.findall(r'\w+',text.casefold(),flags=re.UNICODE)))
        if not terms:continue
        cues=_cue_terms(terms,_term_df(con,terms),min_sim,budget)
        if not cues:
            skipped+=1;continue
        peers=_candidates(con,hid,cues,limit)
        if not peers:continue
        obs_rows={r[0]:r for r in con.execute(_OBS_SQL.format(','.join('?'*(len(peers)+1))),[hid]+peers)}
        own=obs_rows.get(hid)
        if own is None:continue
        ta=re.findall(r'\w+',own[1].casefold(),flags=re.UNICODE)
        for other in peers:
            a,b=sorted((hid,other));key=str(a)+':'+str(b)
            if key in seen or other not in obs_rows:continue
            seen.add(key);examined+=1
            tb=re.findall(r'\w+',obs_rows[other][1].casefold(),flags=re.UNICODE)
            # Cheap upper bounds first; the ratio can only be lower.
            m=difflib.SequenceMatcher(None,ta,tb,autojunk=False)
            if m.real_quick_ratio()<min_sim or m.quick_ratio()<min_sim:continue
            ra,rb=obs_rows[a],obs_rows[b]
            contrast=text_contrast(ra[1],rb[1],min_sim,min_shared)
            if contrast is None:continue
            existing=con.execute('SELECT contradiction_id FROM semantic_text_contrasts WHERE pair_key=?',(key,)).fetchone()
            anchors=[t for x in contrast['anchors'] for t in x['tokens']]
            kind=_classify_pair(con,key,a,b,contrast,(ra,rb),_term_df(con,list(dict.fromkeys(anchors))),
                                n_index,state,ctx,cid=existing[0] if existing else None)
            contrasts+=int(kind=='contrast')
    backfilled=_backfill_frames(con,state,ctx,n_index)
    _set(con,'scan_checkpoint',scan)
    _set(con,'contrasts_created_total',int(state['contrasts_created_total'])+ctx['created'])
    _set(con,'frames_created_total',int(state['frames_created_total'])+ctx['frames_created'])
    _set(con,'frame_pairs_total',int(state['frame_pairs_total'])+ctx['frame_pairs'])
    _set(con,'observations_skipped_total',int(state['observations_skipped_total'])+skipped)
    _set(con,'gaps_superseded_total',int(state['gaps_superseded_total'])+ctx['superseded'])
    return {'created':ctx['created'],'pairs_examined':examined,'indexed':len(fresh),'observations_scanned':len(rows),
            'observations_without_specific_cue':skipped,'frame_pairs':ctx['frame_pairs'],
            'frames_created':ctx['frames_created'],'contrast_pairs':contrasts,'gaps_superseded':ctx['superseded'],
            'backfilled':backfilled,'semantic_status':'unverified','automatic_truth_decisions':0}
