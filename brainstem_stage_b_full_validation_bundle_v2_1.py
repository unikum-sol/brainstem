from __future__ import annotations
import argparse,ast,base64,hashlib,json,math,os,py_compile,shutil,sqlite3,subprocess,sys,tempfile,time,traceback
from pathlib import Path
VERSION="2.1"
CORE=("dopamine","serotonin","glutamate","gaba","noradrenaline","acetylcholine")
PROTECTED=("facts","relations","questions","internal_learning_gaps","attention_queue","phase5g_experiment_outcomes","phase5g_strategy_experiments","phase5i_outcome_driven_experiments","phase5f_context_expansion_experiments")
REQUIRED=("autonomous.py","db_bootstrap.py","phase_registry.py","gui_app.py","v8_phase7c_adaptive_boundaries_and_ei_balance_release.py","v8_phase7d_slow_wave_sleep_substructure_release.py","v8_phase7cort_stability_watch_release.py","v8_cooperative_core_neuromodulator_sleep_authority_release.py","v8_stageb_guarded_hypothesis_graduation_release.py","v8_stageb_gapflow_runtime_contract_release.py")
RUNNER_B64="aW1wb3J0IGpzb24sc3lzLHRyYWNlYmFjayx0aW1lCmZyb20ga2lfc3lzdGVtLm1lbW9yeSBpbXBvcnQgTWVtb3J5CmZyb20ga2lfc3lzdGVtLmF1dG9ub21vdXMgaW1wb3J0IEF1dG9ub21vdXNMb29wCm91dD17ImN5Y2xlc19yZXF1ZXN0ZWQiOmludChzeXMuYXJndlsxXSksImN5Y2xlc19jb21wbGV0ZWQiOjAsImVycm9ycyI6W119CnN0YXJ0ZWQ9dGltZS50aW1lKCk7bGFzdD10aW1lLnRpbWUoKQpwcmludCgiW1NUQUdFQl0gcnVudGltZV9zdGFydCBjeWNsZXM9JWQiICUgb3V0WyJjeWNsZXNfcmVxdWVzdGVkIl0sZmx1c2g9VHJ1ZSkKdHJ5OgogbT1NZW1vcnkoImtpX21lbW9yeS5zcWxpdGUzIik7bG9vcD1BdXRvbm9tb3VzTG9vcChtKQogZm9yIGkgaW4gcmFuZ2Uob3V0WyJjeWNsZXNfcmVxdWVzdGVkIl0pOgogIHRyeToKICAgbG9vcC5jeWNsZSgpO291dFsiY3ljbGVzX2NvbXBsZXRlZCJdKz0xCiAgIG5vdz10aW1lLnRpbWUoKTtkb25lPW91dFsiY3ljbGVzX2NvbXBsZXRlZCJdCiAgIGlmIGRvbmU9PTEgb3IgZG9uZSU1PT0wIG9yIGRvbmU9PW91dFsiY3ljbGVzX3JlcXVlc3RlZCJdOgogICAgcGN0PTEwMC4wKmRvbmUvbWF4KDEsb3V0WyJjeWNsZXNfcmVxdWVzdGVkIl0pCiAgICBwcmludCgiU1RBR0VCX1BST0dSRVNTIGN5Y2xlPSVkLyVkIHBlcmNlbnQ9JS4xZiBlbGFwc2VkX3M9JS4xZiBsYXN0X2N5Y2xlX3M9JS4xZiIgJSAoZG9uZSxvdXRbImN5Y2xlc19yZXF1ZXN0ZWQiXSxwY3Qsbm93LXN0YXJ0ZWQsbm93LWxhc3QpLGZsdXNoPVRydWUpCiAgIGxhc3Q9bm93CiAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICBvdXRbImVycm9ycyJdLmFwcGVuZCh7ImN5Y2xlIjppKzEsInR5cGUiOnR5cGUoZSkuX19uYW1lX18sImVycm9yIjpzdHIoZSksInRyYWNlIjp0cmFjZWJhY2suZm9ybWF0X2V4YygpfSk7cHJpbnQoIlNUQUdFQl9SVU5USU1FX0VSUk9SIGN5Y2xlPSVkIHR5cGU9JXMgZXJyb3I9JXMiICUgKGkrMSx0eXBlKGUpLl9fbmFtZV9fLHN0cihlKSksZmx1c2g9VHJ1ZSk7YnJlYWsKIHRyeTptLmRiLmNvbW1pdCgpCiBleGNlcHQgRXhjZXB0aW9uOnBhc3MKZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogb3V0WyJlcnJvcnMiXS5hcHBlbmQoeyJjeWNsZSI6MCwidHlwZSI6dHlwZShlKS5fX25hbWVfXywiZXJyb3IiOnN0cihlKSwidHJhY2UiOnRyYWNlYmFjay5mb3JtYXRfZXhjKCl9KTtwcmludCgiU1RBR0VCX1JVTlRJTUVfRVJST1IgY3ljbGU9MCB0eXBlPSVzIGVycm9yPSVzIiAlICh0eXBlKGUpLl9fbmFtZV9fLHN0cihlKSksZmx1c2g9VHJ1ZSkKcHJpbnQoIlNUQUdFQl9SVU5USU1FX0pTT049Iitqc29uLmR1bXBzKG91dCxzb3J0X2tleXM9VHJ1ZSksZmx1c2g9VHJ1ZSkK"
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def qi(n):return '"'+n.replace('"','""')+'"'
def exists(c,t):return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def cnt(c,t):return int(c.execute("SELECT COUNT(*) FROM "+qi(t)).fetchone()[0])
def kv(c,t):
 if not exists(c,t):return {}
 cols={r[1] for r in c.execute("PRAGMA table_info("+qi(t)+")")}
 return dict(c.execute("SELECT key,value FROM "+qi(t)).fetchall()) if {"key","value"}<=cols else {}
def num(v):
 try:
  x=float(v);return x if math.isfinite(x) else None
 except Exception:return None
def snapshot(db):
 c=sqlite3.connect("file:"+db.as_posix()+"?mode=ro",uri=True,timeout=30)
 try:
  ts={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  core=kv(c,"phase6a_neuromodulated_sleep_state")
  grad={t:cnt(c,t) for t in ts if "graduat" in t.lower() and not t.startswith("sqlite_")}
  return {"integrity":c.execute("PRAGMA integrity_check").fetchall(),"quick":c.execute("PRAGMA quick_check").fetchall(),"tables":len(ts),"protected":{t:cnt(c,t) for t in PROTECTED if t in ts},"core":{k:num(core.get(k)) for k in CORE},"cooperative":kv(c,"cooperative_sleep_wake_state"),"graduation":grad}
 finally:c.close()
def source_check(root):
 pkg=root/"ki_system";fail=[]
 for n in REQUIRED:
  p=pkg/n
  if not p.is_file():fail.append("missing_module:"+n);continue
  try:ast.parse(p.read_text(encoding="utf-8"));py_compile.compile(str(p),doraise=True)
  except Exception as e:fail.append("compile:"+n+":"+str(e))
 py=list(pkg.glob("*.py"))
 for p in py:
  try:py_compile.compile(str(p),doraise=True)
  except Exception as e:fail.append("compile_all:"+p.name+":"+str(e))
 req={"phase_registry.py":["v8_cooperative_core_neuromodulator_sleep_authority_release","v8_stageb_guarded_hypothesis_graduation_release"],"v8_phase7c_adaptive_boundaries_and_ei_balance_release.py":["def _soft_clamp","sigmoid_soft_clipping"],"v8_phase7d_slow_wave_sleep_substructure_release.py":["Efraimidis-Spirakis","cooperative_sleep_wake_state"],"v8_cooperative_core_neuromodulator_sleep_authority_release.py":["SCHEMA_TABLES","def ensure_schema","def _self_check_schema"],"v8_stageb_guarded_hypothesis_graduation_release.py":["_critic_gate"]}
 for fn,toks in req.items():
  body=(pkg/fn).read_text(encoding="utf-8",errors="replace") if (pkg/fn).is_file() else ""
  for tok in toks:
   if tok not in body:fail.append("missing_contract:"+fn+":"+tok)
 coop=(pkg/"v8_cooperative_core_neuromodulator_sleep_authority_release.py").read_text(encoding="utf-8",errors="replace").lower()
 for tok in ("insert into facts","update facts","insert into relations","update relations","insert into questions","update questions"):
  if tok in coop:fail.append("forbidden_cooperative_write:"+tok)
 return fail,{"python_files":len(py),"required_modules":len(REQUIRED)}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--root",default=".");ap.add_argument("--db",default="ki_memory.sqlite3");ap.add_argument("--cycles",type=int,default=1344);ap.add_argument("--keep-sandbox",action="store_true");a=ap.parse_args()
 root=Path(a.root).resolve();db=(root/a.db).resolve() if not Path(a.db).is_absolute() else Path(a.db).resolve();cycles=max(1,a.cycles);fail=[];warnings=[];start=time.time()
 print("[STAGEB] full_validation_bundle version=2.1 target_cycles=%d" % cycles,flush=True)
 if not (root/"ki_system").is_dir():raise SystemExit("PROJECT_ROOT_INVALID")
 if not db.is_file():raise SystemExit("DATABASE_NOT_FOUND:"+str(db))
 sf,source=source_check(root);fail+=sf;hash0={p.name:sha(p) for p in (root/"ki_system").glob("*.py")};before=snapshot(db)
 if before["integrity"]!=[("ok",)]:fail.append("live_integrity_failed")
 if before["quick"]!=[("ok",)]:fail.append("live_quick_check_failed")
 work=Path(tempfile.mkdtemp(prefix="brainstem_stageb_"));sand=work/"sandbox";sand.mkdir();dbcopy=sand/"ki_memory.sqlite3";shutil.copy2(db,dbcopy);run=sand/"runner.py";run.write_bytes(base64.b64decode(RUNNER_B64))
 env=os.environ.copy();env["PYTHONPATH"]=str(root)+(os.pathsep+env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
 print("[STAGEB] source_and_database_preflight=PASS",flush=True)
 print("[STAGEB] sandbox_runtime_start cycles=%d progress_interval=5" % cycles,flush=True)
 runtime={"returncode":None,"cycles_completed":0,"errors":[],"stdout_tail":"","stderr_tail":"","last_progress_cycle":0}
 proc=None;captured=[]
 try:
  proc=subprocess.Popen([sys.executable,str(run),str(cycles)],cwd=str(sand),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
  deadline=time.time()+max(300,cycles*120)
  for raw in iter(proc.stdout.readline,""):
   line=raw.rstrip("\r\n");captured.append(line)
   if len(captured)>400:captured=captured[-400:]
   if line.startswith("STAGEB_PROGRESS ") or line.startswith("[STAGEB]") or line.startswith("STAGEB_RUNTIME_ERROR"):
    print(line,flush=True)
   if line.startswith("STAGEB_PROGRESS "):
    try:runtime["last_progress_cycle"]=int(line.split("cycle=",1)[1].split("/",1)[0])
    except Exception:pass
   if line.startswith("STAGEB_RUNTIME_JSON="):
    try:runtime.update(json.loads(line.split("=",1)[1]))
    except Exception:pass
   if time.time()>deadline:
    proc.kill();fail.append("runtime_timeout");break
  proc.wait(timeout=30);runtime["returncode"]=proc.returncode;runtime["stdout_tail"]="\n".join(captured)[-12000:]
 except Exception as e:
  if proc and proc.poll() is None:proc.kill()
  fail.append("runtime_subprocess:"+type(e).__name__+":"+str(e))
 if runtime.get("returncode") not in (0,None):fail.append("runtime_subprocess_nonzero")
 print("[STAGEB] sandbox_runtime_end completed=%s/%s returncode=%s" % (runtime.get("cycles_completed"),cycles,runtime.get("returncode")),flush=True)
 if runtime.get("cycles_completed")!=cycles:fail.append("runtime_cycles_incomplete")
 if runtime.get("errors"):fail.append("runtime_errors_present")
 after=snapshot(dbcopy)
 if after["integrity"]!=[("ok",)]:fail.append("sandbox_integrity_failed")
 for t,v in before["protected"].items():
  if after["protected"].get(t,v)!=v:fail.append("protected_table_changed:"+t+":"+str(v)+"->"+str(after["protected"].get(t)))
 deltas={k:None if before["core"].get(k) is None or after["core"].get(k) is None else round(after["core"][k]-before["core"][k],9) for k in CORE}
 if any(after["core"].get(k) is None for k in CORE):fail.append("missing_or_nonfinite_core")
 if all(v is None or abs(v)<=1e-12 for v in deltas.values()):fail.append("six_core_no_observed_delta")
 coop=after["cooperative"];state=str(coop.get("state","")).lower();score=num(coop.get("sleep_score"))
 if state not in ("wake","sleep"):fail.append("cooperative_state_invalid")
 if score is None or not 0<=score<=1:fail.append("cooperative_sleep_score_invalid")
 hash1={p.name:sha(p) for p in (root/"ki_system").glob("*.py")}
 if hash0!=hash1:fail.append("source_changed_during_test")
 result={"title":"BrainStem Full Stage-B 1,344-Cycle Validation Bundle","version":VERSION,"verdict":"STAGE_B_TECHNICAL_VALIDATION_PASS" if not fail else "STAGE_B_NOT_READY","stage_b_ready_candidate":not fail,"full_1344_cycle_stability_validated":(not fail and cycles==1344),"failures":fail,"warnings":warnings,"cycles_requested":cycles,"source":source,"live_before":before,"sandbox_after":after,"runtime":runtime,"six_core_deltas":deltas,"cooperative_sleep":{"state":state,"score":score,"transition_reason":coop.get("transition_reason"),"cycle_count":coop.get("cycle_count")},"protected_table_invariance":not any(x.startswith("protected_table_changed:") for x in fail),"source_invariance":hash0==hash1,"duration_seconds":round(time.time()-start,3),"evidence_status":{"full_1344_cycle_stability":(not fail and cycles==1344),"long_run_drift_control":(not fail and cycles==1344),"natural_sleep_state_measured":bool(coop),"gui_endurance":"NOT_EVALUATED_BY_HEADLESS_RUN","semantic_effectiveness":"NOT_EVALUATED_WITHOUT_BENCHMARK","real_user_usefulness":"NOT_EVALUATED_WITHOUT_USER_EVIDENCE","facts_promotion_enabled":False},"promotion_readiness":{"readiness_only":True,"facts_promotion_remains_closed":True,"protected_facts_unchanged":not any(x.startswith("protected_table_changed:facts") for x in fail)},"limitations":["All runtime cycles run against an isolated copy of the live database.","The headless run validates backend stability and bounded state behavior, not physical Tkinter rendering endurance.","Semantic effectiveness requires a fixed before/after benchmark.","Real-user usefulness requires actual user evaluation evidence."]}
 report=root/"stage_b_full_validation_report.json";report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps({"verdict":result["verdict"],"stage_b_ready_candidate":result["stage_b_ready_candidate"],"failures":fail,"report":str(report)},ensure_ascii=False,sort_keys=True))
 if not a.keep_sandbox:shutil.rmtree(work,ignore_errors=True)
 return 0 if not fail else 2
if __name__=="__main__":raise SystemExit(main())
