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
    names=['zimdump.exe','zimdump']; dirs=[Path.cwd(),Path(__file__).resolve().parents[1]]
    if getattr(sys,'frozen',False): dirs.insert(0,Path(sys.executable).resolve().parent)
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
                    if len(t)>2 and not t.lower().endswith(MEDIA): titles.append(t)
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
        titles=list_zim_titles(p,max_articles,progress,cancel); ci=0
        for n,t in enumerate(titles,1):
            if cancel and cancel(): break
            if progress: progress(n,len(titles),f'ZIM {n}/{len(titles)} {t[:60]}')
            txt=show_zim_article(p,t)
            for ch in chunk_text(txt):
                memory.add_chunk(doc,ci,ch,{'article':t},f'{p}::{t}::{ci}'); ci+=1; total+=1
        return {'document_id':doc,'chunks':total,'kind':kind,'title':p.stem}
    else: raise IngestError('Nicht unterstütztes Format: '+p.suffix)
    ci=0
    for title,txt,idx in articles:
        for ch in chunk_text(txt): memory.add_chunk(doc,ci,ch,{'article':title},f'{p}::{title}::{ci}'); ci+=1; total+=1
    return {'document_id':doc,'chunks':total,'kind':kind,'title':p.stem}
