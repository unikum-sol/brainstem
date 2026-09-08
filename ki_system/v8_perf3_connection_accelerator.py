# -*- coding: utf-8 -*-
"""
V8 Perf3 - Global Connection Accelerator

Wraps sqlite3.connect so EVERY new connection automatically gets the fast
PRAGMAs (WAL, synchronous=NORMAL, 256MB cache, temp in memory, 1GB mmap).

Root-cause fix: the profiler and the GUI each open their own Memory()
connection. perf0 only set PRAGMAs on the connection that existed at
autoload time. This makes the settings apply to ALL connections opened
after this module is loaded.

Safe: only changes durability/cache tuning, never data. WAL keeps crash
safety. No learning logic touched.
"""
import sqlite3

_orig_connect = sqlite3.connect

def _fast_connect(*args, **kwargs):
    con = _orig_connect(*args, **kwargs)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        con.execute("PRAGMA cache_size=-262144")
        con.execute("PRAGMA temp_store=MEMORY")
        con.execute("PRAGMA mmap_size=1073741824")
    except Exception:
        pass
    return con

def install_global_accelerator():
    if getattr(sqlite3, "_perf3_installed", False):
        return False
    sqlite3.connect = _fast_connect
    sqlite3._perf3_installed = True
    return True

def autoload(AutonomousLoop):
    install_global_accelerator()
    AutonomousLoop.perf3_connection_accelerator = True
    return AutonomousLoop
