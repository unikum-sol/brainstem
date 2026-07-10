from __future__ import annotations
import json
import re
import time
from collections import Counter

WORD_RE = re.compile(r'[A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9+.#-]*')
ACRONYM_RE = re.compile(r'^[A-Z0-9][A-Z0-9+.#-]{1,18}$')
DATE_RE = re.compile(r'^(seit\s+)?(anfang|mitte|ende|januar|februar|märz|maerz|april|mai|juni|juli|august|september|oktober|november|dezember)\s+\d{4}\b|^\d{4}$', re.I)

STOP_TOKENS = set('der die das ein eine einer eines einem einen und oder aber jedoch sowie auch noch mehr sehr mit von für fuer auf in im am an als bei zu zur zum des den dem ist sind war waren wird wurde werden durch aus nach über ueber unter nicht nur bis seit dabei damit deshalb daher häufig haeufig zuvor heute seitdem ursprünglich urspruenglich mittlerweile oft neu bekannt was'.split())
GENERIC_DOC_TITLES = ('wikipedia_', 'wiki_', 'zim_', 'dump_', 'articles_', 'computer_maxi')
BAD_ROLE_SUBJECTS = set('neu heute seitdem mittlerweile ursprünglich urspruenglich oft zudem damit daher deshalb zuvor bekannt was nachfolger ausschlaggebend allerdings'.split())
WEAK_ARTICLE_SUBJECTS = {'die erste','der erste','das erste','ein erster','eine erste','die zweite','der zweite','das zweite','die letzte','der letzte','das letzte','die einzige','der einzige','das einzige'}
ENTITY_HINT_WORDS = set('framework protokoll protocol server client domain cpu gpu prozessor mikroprozessor betriebssystem software unternehmen sprache format dateiformat standard algorithmus algoritmus architektur netzwerk datenbank programm bibliothek schnittstelle projekt system'.split())


def norm_text(value):
    return ' '.join(str(value or '').replace('_', ' ').split()).strip()

def norm_key(value):
    return norm_text(value).lower()[:180]

def tokens(value):
    return [t.lower() for t in WORD_RE.findall(norm_text(value)) if t.lower() not in STOP_TOKENS and len(t) > 1]

def token_count(value):
    return len(WORD_RE.findall(norm_text(value)))

class AlignmentRoleLearner:
    def __init__(self, memory):
        self.memory = memory
        self.ensure_schema()
        self.state = self.load_state()

    def ensure_schema(self):
        with self.memory.lock:
            db = self.memory.db
            db.execute("""CREATE TABLE IF NOT EXISTS alignment_role_state(key TEXT PRIMARY KEY,value_json TEXT,updated_at INTEGER)""")
            db.execute("""CREATE TABLE IF NOT EXISTS token_role_stats(token TEXT PRIMARY KEY,entity_count INTEGER DEFAULT 0,fragment_count INTEGER DEFAULT 0,temporal_count INTEGER DEFAULT 0,generic_count INTEGER DEFAULT 0,confidence REAL DEFAULT 0,role TEXT,updated_at INTEGER)""")
            db.execute("""CREATE TABLE IF NOT EXISTS subject_role_stats(subject TEXT PRIMARY KEY,accepted_count INTEGER DEFAULT 0,rejected_count INTEGER DEFAULT 0,last_role TEXT,last_reason TEXT,alignment_avg REAL DEFAULT 0,updated_at INTEGER)""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_subject_role_stats_rejected ON subject_role_stats(rejected_count DESC, accepted_count ASC)")
            db.commit()

    def load_state(self):
        row = self.memory.db.execute("SELECT value_json FROM alignment_role_state WHERE key='state'").fetchone()
        if row:
            try:
                state = json.loads(row['value_json'])
                if isinstance(state, dict):
                    state['version'] = 'phase3d6j_fixed'
                    state.setdefault('min_alignment_score', 0.18)
                    state.setdefault('entity_role_min_score', 0.35)
                    state.setdefault('total_seen', 0)
                    state.setdefault('total_low_alignment', 0)
                    return state
            except Exception:
                pass
        state = {'version':'phase3d6j_fixed','min_alignment_score':0.18,'entity_role_min_score':0.35,'total_seen':0,'total_low_alignment':0,'last_consolidation_seen':0}
        self.save_state(state)
        return state

    def save_state(self, state=None):
        state = state or self.state
        with self.memory.lock:
            self.memory.db.execute("INSERT OR REPLACE INTO alignment_role_state(key,value_json,updated_at) VALUES(?,?,?)", ('state', json.dumps(state, ensure_ascii=False), int(time.time())))
            self.memory.db.commit()

    def _context_terms(self, context_title='', text=''):
        ctx = norm_text(context_title); ctx_l = ctx.lower(); terms=[]
        if ctx and not any(marker in ctx_l for marker in GENERIC_DOC_TITLES):
            terms.extend(tokens(ctx))
        terms.extend(tokens(norm_text(text[:700]))[:80])
        return Counter(terms)

    def subject_role(self, subject):
        s = norm_text(subject); sl = s.lower(); tc = token_count(s)
        if not s: return 'empty', 0.0
        if sl in WEAK_ARTICLE_SUBJECTS:
            return 'weak_article_fragment', 0.05
        if sl in BAD_ROLE_SUBJECTS or DATE_RE.search(sl):
            return 'temporal_or_adverbial', 0.05
        if s[0].islower() and tc > 2:
            return 'clause_fragment', 0.12
        if tc > 10:
            return 'sentence_fragment', 0.10
        if (' und ' in sl or ' oder ' in sl) and tc > 5:
            return 'coordinated_fragment', 0.15
        if ACRONYM_RE.match(s) or any(ch.isdigit() for ch in s) or any(tok in ENTITY_HINT_WORDS for tok in tokens(s)):
            return 'entity_like', 0.72
        if s[:1].isupper() and 1 <= tc <= 6:
            return 'entity_like', 0.56
        if sl.startswith(('die ', 'der ', 'das ', 'ein ', 'eine ')) and tc <= 5:
            # Article phrases are only weak noun phrases unless they carry a real entity hint.
            if any(tok in ENTITY_HINT_WORDS for tok in tokens(s)):
                return 'noun_phrase', 0.42
            return 'generic_noun_phrase', 0.22
        if sl.startswith(('die ', 'der ', 'das ', 'ein ', 'eine ')) and tc > 5:
            return 'generic_noun_phrase', 0.20
        return 'unknown', 0.30

    def alignment_score(self, subject, obj='', context_title='', text=''):
        st = tokens(subject); ot = tokens(obj); ctx_terms = self._context_terms(context_title, text)
        if not st: return 0.0, {'overlap': [], 'subject_role': 'empty'}
        overlap = [t for t in st if ctx_terms.get(t, 0) > 0]
        role, role_score = self.subject_role(subject)
        score = 0.0
        if overlap: score += min(0.45, 0.15 * len(set(overlap)))
        score += role_score * 0.35
        obj_overlap = [t for t in ot[:6] if ctx_terms.get(t, 0) > 0]
        if obj_overlap: score += min(0.15, 0.05 * len(set(obj_overlap)))
        if role in ('temporal_or_adverbial','clause_fragment','sentence_fragment','coordinated_fragment','weak_article_fragment','generic_noun_phrase'):
            score -= 0.20
        return max(0.0, min(1.0, score)), {'overlap': overlap[:8], 'object_overlap': obj_overlap[:8], 'subject_role': role, 'role_score': role_score}

    def evaluate(self, subject, relation, obj, context_title='', text=''):
        align, details = self.alignment_score(subject, obj, context_title, text)
        role = details.get('subject_role', 'unknown')
        min_align = float(self.state.get('min_alignment_score', 0.18))
        min_role = float(self.state.get('entity_role_min_score', 0.35))
        role_score = float(details.get('role_score', 0.0))
        allowed = True; reason = 'alignment_ok'
        if role in ('temporal_or_adverbial','clause_fragment','sentence_fragment','coordinated_fragment','weak_article_fragment'):
            allowed = False; reason = 'role_' + role
        elif role == 'generic_noun_phrase' and align < (min_align + 0.10):
            allowed = False; reason = 'generic_subject_low_alignment'
        elif align < min_align and role_score < min_role:
            allowed = False; reason = 'low_context_alignment'
        elif role == 'unknown' and align < (min_align + 0.08):
            allowed = False; reason = 'unknown_subject_low_alignment'
        return allowed, reason, align, details

    def observe(self, subject, accepted, reason, alignment, role_details=None):
        role_details = role_details or {}; subject_key = norm_key(subject)
        if not subject_key: return
        self.state['total_seen'] = int(self.state.get('total_seen', 0)) + 1
        if not accepted and ('alignment' in reason or reason.startswith('role_') or reason.startswith('generic_subject')):
            self.state['total_low_alignment'] = int(self.state.get('total_low_alignment', 0)) + 1
        now = int(time.time()); role = role_details.get('subject_role', 'unknown')
        with self.memory.lock:
            row = self.memory.db.execute("SELECT * FROM subject_role_stats WHERE subject=?", (subject_key,)).fetchone()
            if row:
                ac = int(row['accepted_count'] or 0) + (1 if accepted else 0); rc = int(row['rejected_count'] or 0) + (0 if accepted else 1)
                old_avg = float(row['alignment_avg'] or 0.0); n = max(1, ac + rc); avg = ((old_avg * (n - 1)) + float(alignment or 0.0)) / n
                self.memory.db.execute("UPDATE subject_role_stats SET accepted_count=?, rejected_count=?, last_role=?, last_reason=?, alignment_avg=?, updated_at=? WHERE subject=?", (ac, rc, role, reason, avg, now, subject_key))
            else:
                self.memory.db.execute("INSERT INTO subject_role_stats(subject,accepted_count,rejected_count,last_role,last_reason,alignment_avg,updated_at) VALUES(?,?,?,?,?,?,?)", (subject_key, 1 if accepted else 0, 0 if accepted else 1, role, reason, float(alignment or 0.0), now))
            for tok in tokens(subject)[:8]:
                trow = self.memory.db.execute("SELECT * FROM token_role_stats WHERE token=?", (tok,)).fetchone()
                inc = {'entity_count':0,'fragment_count':0,'temporal_count':0,'generic_count':0}
                if role == 'entity_like' or (accepted and role == 'noun_phrase'): inc['entity_count'] = 1
                elif role == 'temporal_or_adverbial': inc['temporal_count'] = 1
                elif role in ('clause_fragment','sentence_fragment','coordinated_fragment','weak_article_fragment'): inc['fragment_count'] = 1
                else: inc['generic_count'] = 1
                if trow:
                    vals = {k:int(trow[k] or 0)+v for k,v in inc.items()}; total = max(1, sum(vals.values()))
                    best_key = max(vals, key=vals.get); best_role = best_key.replace('_count',''); conf = vals[best_key] / total
                    self.memory.db.execute("UPDATE token_role_stats SET entity_count=?,fragment_count=?,temporal_count=?,generic_count=?,confidence=?,role=?,updated_at=? WHERE token=?", (vals['entity_count'], vals['fragment_count'], vals['temporal_count'], vals['generic_count'], conf, best_role, now, tok))
                else:
                    vals = inc; total = max(1, sum(vals.values())); best_key = max(vals, key=vals.get); best_role = best_key.replace('_count',''); conf = vals[best_key] / total
                    self.memory.db.execute("INSERT INTO token_role_stats(token,entity_count,fragment_count,temporal_count,generic_count,confidence,role,updated_at) VALUES(?,?,?,?,?,?,?,?)", (tok, vals['entity_count'], vals['fragment_count'], vals['temporal_count'], vals['generic_count'], conf, best_role, now))
            self.memory.db.commit()
        self.save_state()

    def consolidate(self):
        seen = int(self.state.get('total_seen', 0)); last = int(self.state.get('last_consolidation_seen', 0))
        if seen - last < 250: return {'status':'skip','reason':'interval_not_reached','total_seen':seen}
        low = int(self.state.get('total_low_alignment', 0)); ratio = low / max(1, seen)
        if ratio > 0.35:
            self.state['min_alignment_score'] = min(0.35, float(self.state.get('min_alignment_score', 0.18)) + 0.02)
            self.state['entity_role_min_score'] = min(0.50, float(self.state.get('entity_role_min_score', 0.35)) + 0.015)
        elif ratio < 0.12:
            self.state['min_alignment_score'] = max(0.14, float(self.state.get('min_alignment_score', 0.18)) - 0.01)
        self.state['last_consolidation_seen'] = seen; self.save_state()
        return {'status':'consolidated','low_alignment_ratio':round(ratio,3),'min_alignment_score':round(float(self.state['min_alignment_score']),3),'entity_role_min_score':round(float(self.state['entity_role_min_score']),3)}

    def summary(self):
        cur = self.memory.db
        sr = cur.execute("SELECT COUNT(*) AS c FROM subject_role_stats").fetchone()
        tr = cur.execute("SELECT COUNT(*) AS c FROM token_role_stats").fetchone()
        return {'state':dict(self.state),'subject_role_stats':int(sr['c'] if sr else 0),'token_role_stats':int(tr['c'] if tr else 0)}
