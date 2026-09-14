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
    return ''
def import_file(path,memory,max_articles=2000,progress=None,cancel=None,resume=True):
    p=Path(path); kind=p.suffix.lower().lstrip('.'); total=0; doc=memory.add_document(p,p.stem,kind,{'suffix':p.suffix})
    if p.suffix.lower()=='.txt': articles=[(p.stem,read_text(p),0)]
    elif p.suffix.lower()=='.pdf': articles=[(p.stem,read_pdf(p),0)]
    elif p.suffix.lower()=='.zim':
        titles=list_zim_titles(p,max_articles,progress,cancel)
        # BRAINSTEM_INGEST_RESUME_AND_DUPLICATE_COUNT_FIX_V1
        #
        # Root cause 1 (duplicate counting): total+=1 previously ran
        # unconditionally after every memory.add_chunk() call, regardless
        # of whether a chunk was actually newly inserted. add_chunk() uses
        # "INSERT OR IGNORE" keyed on a unique import_key and returns None
        # when the row already existed (a silent duplicate skip) or the
        # new row's id otherwise. Re-importing the same source (e.g. after
        # a cancelled run, or the same file twice) therefore inflated the
        # reported "chunks" count with chunks that were never actually
        # written. Fixed by only counting when add_chunk() returns a
        # non-None id.
        #
        # Root cause 2 (resume unused): the "resume" parameter was declared
        # with a default of True but never referenced anywhere in this
        # function body -- a large, potentially multi-hour ZIM import
        # (this project's own real corpus reached 167,661 chunks) had no
        # way to skip already-fully-processed articles after a cancel or
        # crash, despite Memory already providing fully-implemented
        # get_import_state()/set_import_state() persistence for exactly
        # this purpose (path, last_article, last_chunk, status), which was
        # simply never called from here. Fixed by wiring resume into the
        # ZIM branch: when resume=True (the default) and a prior,
        # not-yet-"complete" import_state row exists for this exact path,
        # processing continues from the persisted article index and chunk
        # index instead of starting over from article 1 / chunk 0. The
        # chunk-index counter (ci) is resumed too (not merely the article
        # position), so chunk_index values remain a consistent, gap-free,
        # non-duplicated sequence across a resumed run instead of
        # restarting at 0 for the first article processed after resuming.
        # When resume=False, any prior state is ignored and the import
        # starts fresh from article 1 / chunk 0, exactly matching the
        # previous (only) behavior.
        #
        # Scope note: mid-article (sub-article) resume is intentionally
        # not implemented -- resume operates at whole-article granularity,
        # which is the realistic, high-impact case for a large ZIM corpus
        # with many articles, without the added complexity of tracking a
        # partial position within a single article's chunk stream.
        start_index = 0
        ci = 0
        if resume:
            prior = memory.get_import_state(str(p))
            if prior and str(prior.get('status') or '') != 'complete':
                start_index = max(0, min(int(prior.get('last_article') or 0), len(titles)))
                ci = max(0, int(prior.get('last_chunk') or 0))
        # BRAINSTEM_INGEST_RESUME_LAST_DONE_TRACKING_FIX_V1: track the last
        # FULLY-processed article index separately from the raw loop
        # counter "n". Without this, breaking out of the loop right after
        # the cancel-check (before an article's chunks were actually
        # written) would still leave "n" pointing at that not-yet-started
        # article, and persisting that value would cause a subsequent
        # resume to silently skip an article that was never actually
        # imported. last_done is only ever advanced immediately after an
        # article's chunks have been fully written, so a resumed run always
        # continues from the correct, genuinely-completed position.
        last_done = start_index
        for n,t in enumerate(titles,1):
            if n <= start_index: continue
            if cancel and cancel(): break
            if progress: progress(n,len(titles),f'ZIM {n}/{len(titles)} {t[:60]}')
            txt=show_zim_article(p,t)
            for ch in chunk_text(txt):
                if memory.add_chunk(doc,ci,ch,{'article':t},f'{p}::{t}::{ci}') is not None: total+=1
                ci+=1
            last_done = n
            memory.set_import_state(str(p), last_done, ci, 'in_progress')
        memory.set_import_state(str(p), last_done, ci, 'cancelled' if (cancel and cancel()) else 'complete')
        return {'document_id':doc,'chunks':total,'kind':kind,'title':p.stem}
    else: raise IngestError('Nicht unterstütztes Format: '+p.suffix)
    ci=0
    for title,txt,idx in articles:
        for ch in chunk_text(txt):
            if memory.add_chunk(doc,ci,ch,{'article':title},f'{p}::{title}::{ci}') is not None: total+=1
            ci+=1
    memory.set_import_state(str(p), len(articles), ci, 'complete')
    return {'document_id':doc,'chunks':total,'kind':kind,'title':p.stem}
