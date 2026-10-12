from pathlib import Path
from shutil import which
import subprocess, sys, os
from ki_system.text_utils import strip_html
class IngestError(RuntimeError): pass
MEDIA=('.jpg','.jpeg','.png','.gif','.webp','.svg','.ogg','.mp3','.mp4','.css','.js','.ico','.ttf','.woff','.pdf')
def read_text(path):
    p=Path(path)
    for e in ('utf-8','utf-8-sig','cp1252','latin-1'):
        try: return p.read_text(encoding=e)
        except UnicodeDecodeError: pass
    return p.read_text(errors='replace')
def read_pdf(path):
    try:
        from PyPDF2 import PdfReader
        r=PdfReader(str(path)); return '\n\n'.join((p.extract_text() or '') for p in r.pages)
    except Exception as e: raise IngestError('PDF benötigt PyPDF2: '+str(e))
def chunk_text(text,max_words=220,overlap=40):
    words=text.split(); step=max(1,max_words-overlap)
    return [' '.join(words[i:i+max_words]) for i in range(0,len(words),step) if words[i:i+max_words]]
def zimdump_candidates():
    names=['zimdump.exe','zimdump']
    # BRAINSTEM_ZIMDUMP_SEARCH_ORDER_FIX_V1: previously Path.cwd() (the
    # current working directory) was searched FIRST, before the project's
    # own directory. If BrainStem is ever launched from an untrusted or
    # attacker-writable working directory, a malicious zimdump.exe placed
    # there would be found and executed in preference to the legitimate,
    # PATH-resolved or project-local binary. Reordered so that the system
    # PATH (via which(), checked first per name below) and the project's
    # own directory are always preferred; the current working directory is
    # now checked LAST, as a convenience fallback only, never a priority
    # location.
    dirs=[Path(__file__).resolve().parents[1]]
    if getattr(sys,'frozen',False): dirs.insert(0,Path(sys.executable).resolve().parent)
    dirs.append(Path.cwd())
    out=[]
    for n in names:
        f=which(n)
        if f: out.append(f)
        for d in dirs:
            p=d/n
            if p.exists(): out.append(str(p))
    return list(dict.fromkeys(out))
def _run(exe,args,timeout=30):
    kw=dict(capture_output=True,text=False,timeout=timeout,stdin=subprocess.DEVNULL)
    if os.name=='nt': kw['creationflags']=getattr(subprocess,'CREATE_NO_WINDOW',0)
    p=subprocess.run([exe]+args,**kw); return p.returncode,p.stdout.decode('utf-8','replace'),p.stderr.decode('utf-8','replace')
def list_zim_titles(path,max_articles,progress=None,cancel=None):
    c=zimdump_candidates()
    if not c: raise IngestError('zimdump.exe wurde nicht gefunden')
    for exe in c:
        try:
            rc,out,err=_run(exe,['list',str(path)],timeout=600)
            if rc==0 and out:
                titles=[]
                for line in out.splitlines():
                    if cancel and cancel(): break
                    t=line.strip()
                    if t and not t.lower().endswith(MEDIA): titles.append(t)
                    if len(titles)>=max_articles: break
                return titles
        except Exception: pass
    raise IngestError('zimdump list fehlgeschlagen')
def show_zim_article(path,title):
    for exe in zimdump_candidates():
        for args in [['show','--url',title,str(path)],['show','--url='+title,str(path)],['show','--url','A/'+title,str(path)]]:
            try:
                rc,out,err=_run(exe,args,timeout=15)
                if rc==0 and out.strip(): return strip_html(out)
            except Exception: pass
    raise IngestError('ZIM article could not be read: ' + str(title))
def _import_document(memory, path, kind):
    # Reuse the original identity; never delete or merge historical rows.
    rows = memory.rows('SELECT id FROM documents WHERE path=? AND kind=? ORDER BY id LIMIT 1', (str(path), kind))
    if rows:
        return rows[0]['id']
    return memory.add_document(path, path.stem, kind, {'suffix': path.suffix})


def import_file(path,memory,max_articles=2000,progress=None,cancel=None,resume=True):
    p = Path(path)
    kind = p.suffix.lower().lstrip('.')
    total = 0
    if p.suffix.lower() not in ('.txt', '.pdf', '.zim'):
        raise IngestError('Unsupported format: ' + p.suffix)
    if not p.is_file():
        raise IngestError('Source file not found: ' + str(p))
    if kind in ('txt', 'pdf'):
        text = read_text(p) if kind == 'txt' else read_pdf(p)
        chunks = chunk_text(text)
        if not chunks:
            raise IngestError('Source contains no readable text: ' + str(p))
        doc = _import_document(memory, p, kind)
        for ci, ch in enumerate(chunks):
            if cancel and cancel():
                return {'document_id': doc, 'chunks': total, 'kind': kind, 'title': p.stem, 'status': 'cancelled'}
            if memory.add_chunk(doc,ci,ch,{'article':p.stem},f'{p}::{p.stem}::{ci}') is not None:
                total += 1
        return {'document_id': doc, 'chunks': total, 'kind': kind, 'title': p.stem, 'status': 'complete'}

    titles = list_zim_titles(p,max_articles,progress,cancel)
    if not titles and not (cancel and cancel()):
        raise IngestError("ZIM listing contains no readable articles: " + str(p))
    prior_row = memory.get_import_state(str(p)) if resume else None
    prior = dict(prior_row) if prior_row is not None else None
    start_index = 0
    ci = 0
    if prior and str(prior.get('status') or '') != 'complete':
        start_index = max(0, min(int(prior.get('last_article') or 0), len(titles)))
        ci = max(0, int(prior.get('last_chunk') or 0))
    last_done = start_index
    doc = None
    cancelled = False
    for n, title in enumerate(titles, 1):
        if n <= start_index:
            continue
        if cancel and cancel():
            cancelled = True
            break
        if progress:
            progress(n, len(titles), f'ZIM {n}/{len(titles)} {title[:60]}')
        try:
            text = show_zim_article(p, title)
            chunks = chunk_text(text)
            if not chunks:
                raise IngestError('ZIM article contains no readable text: ' + str(title))
        except Exception as exc:
            # Stop at the first failed article: the next resume retries it.
            memory.set_import_state(str(p), last_done, ci, 'failed')
            raise IngestError('ZIM import stopped at article ' + str(title)) from exc
        if doc is None:
            doc = _import_document(memory, p, kind)
        for ch in chunks:
            if memory.add_chunk(doc,ci,ch,{'article':title},f'{p}::{title}::{ci}') is not None:
                total += 1
            ci += 1
        last_done = n
        memory.set_import_state(str(p), last_done, ci, 'in_progress')
    if cancel and cancel():
        cancelled = True
    status = 'cancelled' if cancelled else 'complete'
    memory.set_import_state(str(p), last_done, ci, status)
    return {'document_id': doc, 'chunks': total, 'kind': kind, 'title': p.stem, 'status': status}
