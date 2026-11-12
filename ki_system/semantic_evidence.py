"""Evidence-typed surface validation and unverified text contrast discovery.

No language-specific words, negation lists, pretrained model or generated grammar.
A surface contrast is NOT a logical contradiction. Repetition is NOT truth.
"""
import difflib
import json
import re
import time

SCHEMA_TABLES = {
    'semantic_evidence_state': [('key','TEXT PRIMARY KEY'),('value','TEXT'),('updated_at','INTEGER')],
    'semantic_text_contrasts': [
        ('pair_key','TEXT PRIMARY KEY'),('hypothesis_a','INTEGER'),('hypothesis_b','INTEGER'),
        ('contradiction_id','INTEGER'),('gap_id','INTEGER'),('similarity','REAL'),
        ('anchors_json','TEXT'),('differences_json','TEXT'),('evidence_a','INTEGER'),
        ('evidence_b','INTEGER'),('status',"TEXT DEFAULT 'unverified'"),
        ('created_at','INTEGER'),('updated_at','INTEGER'),
    ],
}
DEFAULTS = {'index_checkpoint':'0','scan_checkpoint':'0','scan_batch':'32',
            'peer_limit':'16','min_similarity':'0.65','min_shared_tokens':'3',
            'contrasts_created_total':'0'}


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
    if _columns(con,'stageb_graduation_events'):
        con.execute('CREATE INDEX IF NOT EXISTS idx_semantic_graduation_hypothesis ON stageb_graduation_events(hypothesis_id,id)')
    now=int(time.time())
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
                (key,str(value),int(time.time())))


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


def discover_text_contrasts(con):
    ensure_schema(con)
    from ki_system.v8_stageb_gap_detection_release import _upsert_gap, _neuromodulators, STATE_TABLE as GAP_STATE, ensure_schema as ensure_gap_schema
    ensure_gap_schema(con)
    gap_state = _read_kv(con, GAP_STATE)
    serotonin = _neuromodulators(con)['serotonin']
    habituation_max = max(1, round(float(gap_state.get('habituation_max_stagnant_cycles',64)) *
        (1.0 + float(gap_state.get('selection_pressure_serotonin_gain',0.5)) * (serotonin - 0.5))))
    state=_read_kv(con,'semantic_evidence_state')
    batch=min(128,max(1,int(state['scan_batch'])))
    peers=min(64,max(1,int(state['peer_limit'])))
    checkpoint=int(state['index_checkpoint']);fresh=_observation_rows(con,checkpoint,batch)
    for hid,text in fresh:
        if not con.execute('SELECT 1 FROM semantic_observation_fts WHERE rowid=?',(hid,)).fetchone():
            con.execute('INSERT INTO semantic_observation_fts(rowid,text) VALUES(?,?)',(hid,text))
        checkpoint=hid
    _set(con,'index_checkpoint',checkpoint)
    # Rotate the scan so old candidates can receive real new evidence. No
    # unbounded all-pairs scan and no manual subject merging.
    scan=int(state['scan_checkpoint']);rows=_observation_rows(con,scan,batch)
    if not rows:scan=0;rows=_observation_rows(con,0,batch)
    created=0;examined=0;seen=set();now=int(time.time())
    for hid,text in rows:
        scan=hid
        terms=list(dict.fromkeys(re.findall(r'\w+',text.casefold(),flags=re.UNICODE)))[:12]
        if not terms:continue
        query=' OR '.join('"'+t.replace('"','""')+'"' for t in terms)
        matches=con.execute('SELECT rowid FROM semantic_observation_fts WHERE semantic_observation_fts MATCH ? '
                            'AND rowid<>? ORDER BY bm25(semantic_observation_fts),rowid LIMIT ?',
                            (query,hid,peers)).fetchall()
        for (other,) in matches:
            a,b=sorted((hid,other));key=str(a)+':'+str(b)
            if key in seen:continue
            seen.add(key);examined+=1
            obs=con.execute("SELECT id,text_excerpt,evidence_count,chunk_id,uncertainty FROM context_hypotheses "
                            "WHERE id IN (?,?) AND role IN ('uncertain_hypothesis','stable_hypothesis') "
                            "AND COALESCE(status,'active')='active' ORDER BY id",(a,b)).fetchall()
            if len(obs)!=2:continue
            ra,rb=obs
            contrast=text_contrast(ra[1],rb[1],float(state['min_similarity']),int(state['min_shared_tokens']))
            if contrast is None:continue
            existing=con.execute('SELECT contradiction_id,gap_id FROM semantic_text_contrasts WHERE pair_key=?',(key,)).fetchone()
            details={'evidence_kind':'ordered_surface_contrast','semantic_status':'unverified',
                     'hypothesis_ids':[a,b],'source_chunk_ids':[ra[3],rb[3]],
                     'observed_texts':[ra[1],rb[1]],'alignment':contrast,
                     'no_automatic_resolution':True,'repetition_is_not_truth':True}
            payload=json.dumps(details,ensure_ascii=False,sort_keys=True)
            if existing:
                cid,gid=existing
                # Never promote an unverified contrast to resolvable by frequency.
                con.execute("UPDATE contradictions SET details_json=?,value_a=?,value_b=? WHERE id=? "
                            "AND relation='unverified_text_contrast' AND status='unverified'",(payload,ra[1],rb[1],cid))
            else:
                cid=con.execute('INSERT INTO contradictions(subject,relation,value_a,value_b,status,details_json,created_at) '
                                "VALUES(?,'unverified_text_contrast',?,?,'unverified',?,?)",
                                ('contrast:'+key,ra[1],rb[1],payload,now)).lastrowid
                gid=None;created+=1
            # Reuse existing gap->question->chunk feedback; no generated grammar.
            gapkey='semantic_contrast:'+key
            _upsert_gap(con,gapkey,'unverified_text_contrast',
                        'Observed aligned alternatives; incompatibility and scope are not learned',
                        'uncertain_hypothesis',.5+.3*contrast['similarity'],.5,a,
                        float(ra[4] if ra[4] is not None else 1.),ra[1],int(ra[2] or 0)+int(rb[2] or 0),now,
                        habituation_max=habituation_max)
            gid=con.execute('SELECT id FROM internal_learning_gaps WHERE gap_key=?',(gapkey,)).fetchone()[0]
            con.execute('INSERT INTO semantic_text_contrasts(pair_key,hypothesis_a,hypothesis_b,contradiction_id,gap_id,similarity,'
                        'anchors_json,differences_json,evidence_a,evidence_b,status,created_at,updated_at) '
                        "VALUES(?,?,?,?,?,?,?,?,?,?,'unverified',?,?) ON CONFLICT(pair_key) DO UPDATE SET "
                        'similarity=excluded.similarity,anchors_json=excluded.anchors_json,differences_json=excluded.differences_json,'
                        'evidence_a=excluded.evidence_a,evidence_b=excluded.evidence_b,updated_at=excluded.updated_at',
                        (key,a,b,cid,gid,contrast['similarity'],json.dumps(contrast['anchors'],ensure_ascii=False),
                         json.dumps(contrast['differences'],ensure_ascii=False),ra[2],rb[2],now,now))
    _set(con,'scan_checkpoint',scan)
    _set(con,'contrasts_created_total',int(state['contrasts_created_total'])+created)
    return {'created':created,'pairs_examined':examined,'indexed':len(fresh),'observations_scanned':len(rows),
            'semantic_status':'unverified','automatic_truth_decisions':0}
