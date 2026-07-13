@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul

REM =====================================================================
REM  pack_project_to_txt.bat  (Version 2 - ohne Heredoc)
REM  Packt ein Python-Projekt in maximal 3 .txt-Dateien.
REM  Ausgabe: <projekt>\_export_txt\part1.txt .. part3.txt + INDEX.txt
REM =====================================================================

cd /d "%~dp0"
set "ROOT=%CD%"
set "OUTDIR=%ROOT%\_export_txt"
set "HELPER=%TEMP%\_pack_helper_%RANDOM%.py"

echo.
echo [1/6] Projekt-Root : %ROOT%
echo [1/6] Ausgabeordner: %OUTDIR%
echo [1/6] Helper       : %HELPER%

REM --- Python-Check ---
where python >nul 2>nul
if errorlevel 1 (
    echo [FEHLER] Python wurde nicht gefunden. Bitte Python installieren oder in PATH aufnehmen.
    pause
    exit /b 1
)

REM --- Alten Export loeschen ---
if exist "%OUTDIR%" (
    echo [2/6] Alten Export loeschen...
    rmdir /s /q "%OUTDIR%"
)
mkdir "%OUTDIR%"

echo [3/6] Schreibe temporaeren Python-Helper...

REM --- Helper Zeile fuer Zeile schreiben ---
> "%HELPER%" echo # -*- coding: utf-8 -*-
>>"%HELPER%" echo import os, sys
>>"%HELPER%" echo.
>>"%HELPER%" echo ROOT   = sys.argv[1]
>>"%HELPER%" echo OUTDIR = sys.argv[2]
>>"%HELPER%" echo.
>>"%HELPER%" echo ALLOWED_EXT = {".py",".txt",".md",".json",".yaml",".yml",".ini",".cfg",".toml",".bat",".ps1",".sql"}
>>"%HELPER%" echo EXCLUDE_DIRS = {".git",".hg",".svn","__pycache__",".mypy_cache",".pytest_cache","venv",".venv","env",".env","node_modules","build","dist",".idea",".vscode","_export_txt"}
>>"%HELPER%" echo EXCLUDE_FILES = {"pack_project_to_txt.bat"}
>>"%HELPER%" echo MAX_SINGLE_FILE = 20 * 1024 * 1024
>>"%HELPER%" echo MAX_PARTS = 3
>>"%HELPER%" echo.
>>"%HELPER%" echo def rel(p): return os.path.relpath(p, ROOT)
>>"%HELPER%" echo.
>>"%HELPER%" echo collected = []
>>"%HELPER%" echo excl_dirs_lc  = {x.lower() for x in EXCLUDE_DIRS}
>>"%HELPER%" echo excl_files_lc = {x.lower() for x in EXCLUDE_FILES}
>>"%HELPER%" echo for dirpath, dirnames, filenames in os.walk(ROOT):
>>"%HELPER%" echo     dirnames[:] = [d for d in dirnames if d.lower() not in excl_dirs_lc]
>>"%HELPER%" echo     for fn in filenames:
>>"%HELPER%" echo         if fn.lower() in excl_files_lc: continue
>>"%HELPER%" echo         ext = os.path.splitext(fn)[1].lower()
>>"%HELPER%" echo         if ext not in ALLOWED_EXT: continue
>>"%HELPER%" echo         full = os.path.join(dirpath, fn)
>>"%HELPER%" echo         try: size = os.path.getsize(full)
>>"%HELPER%" echo         except OSError: continue
>>"%HELPER%" echo         if size ^> MAX_SINGLE_FILE:
>>"%HELPER%" echo             print("[SKIP zu gross]", rel(full), size); continue
>>"%HELPER%" echo         collected.append((full, size))
>>"%HELPER%" echo.
>>"%HELPER%" echo if not collected:
>>"%HELPER%" echo     print("[FEHLER] Keine passenden Dateien gefunden."); sys.exit(2)
>>"%HELPER%" echo.
>>"%HELPER%" echo collected.sort(key=lambda x: rel(x[0]).lower())
>>"%HELPER%" echo total = sum(s for _, s in collected)
>>"%HELPER%" echo print("[INFO] Gefundene Dateien:", len(collected))
>>"%HELPER%" echo print("[INFO] Gesamtgroesse   :", total, "bytes")
>>"%HELPER%" echo target = (total // MAX_PARTS) + 1
>>"%HELPER%" echo.
>>"%HELPER%" echo part_index   = 1
>>"%HELPER%" echo part_path    = os.path.join(OUTDIR, "part1.txt")
>>"%HELPER%" echo part_file    = open(part_path, "w", encoding="utf-8", newline="\n")
>>"%HELPER%" echo part_written = 0
>>"%HELPER%" echo files_per_part = {i: 0 for i in range(1, MAX_PARTS + 1)}
>>"%HELPER%" echo bytes_per_part = {i: 0 for i in range(1, MAX_PARTS + 1)}
>>"%HELPER%" echo index_lines    = []
>>"%HELPER%" echo.
>>"%HELPER%" echo for full, size in collected:
>>"%HELPER%" echo     relpath = rel(full)
>>"%HELPER%" echo     header  = "\n===== FILE: " + relpath + " =====\n"
>>"%HELPER%" echo     footer  = "\n===== END FILE: " + relpath + " =====\n"
>>"%HELPER%" echo     try:
>>"%HELPER%" echo         with open(full, "r", encoding="utf-8", errors="replace") as f:
>>"%HELPER%" echo             content = f.read()
>>"%HELPER%" echo     except Exception as e:
>>"%HELPER%" echo         content = "[LESEFEHLER: " + str(e) + "]"
>>"%HELPER%" echo     block = header + content + footer
>>"%HELPER%" echo     block_size = len(block.encode("utf-8"))
>>"%HELPER%" echo     if part_written ^> 0 and (part_written + block_size) ^> target and part_index ^< MAX_PARTS:
>>"%HELPER%" echo         part_file.close()
>>"%HELPER%" echo         part_index += 1
>>"%HELPER%" echo         part_path = os.path.join(OUTDIR, "part" + str(part_index) + ".txt")
>>"%HELPER%" echo         part_file = open(part_path, "w", encoding="utf-8", newline="\n")
>>"%HELPER%" echo         part_written = 0
>>"%HELPER%" echo         print("[INFO] Wechsel zu", os.path.basename(part_path))
>>"%HELPER%" echo     part_file.write(block)
>>"%HELPER%" echo     part_written += block_size
>>"%HELPER%" echo     files_per_part[part_index] += 1
>>"%HELPER%" echo     bytes_per_part[part_index] += block_size
>>"%HELPER%" echo     index_lines.append("part" + str(part_index) + ".txt | " + str(block_size).rjust(10) + " B | " + relpath)
>>"%HELPER%" echo.
>>"%HELPER%" echo part_file.close()
>>"%HELPER%" echo.
>>"%HELPER%" echo for i in range(1, MAX_PARTS + 1):
>>"%HELPER%" echo     p = os.path.join(OUTDIR, "part" + str(i) + ".txt")
>>"%HELPER%" echo     if not os.path.exists(p):
>>"%HELPER%" echo         open(p, "w", encoding="utf-8").close()
>>"%HELPER%" echo.
>>"%HELPER%" echo idx_path = os.path.join(OUTDIR, "INDEX.txt")
>>"%HELPER%" echo with open(idx_path, "w", encoding="utf-8", newline="\n") as idx:
>>"%HELPER%" echo     idx.write("PROJEKT-EXPORT INDEX\n")
>>"%HELPER%" echo     idx.write("Root: " + ROOT + "\n")
>>"%HELPER%" echo     idx.write("Dateien gesamt: " + str(len(collected)) + "\n")
>>"%HELPER%" echo     idx.write("Groesse gesamt: " + str(total) + " bytes\n\n")
>>"%HELPER%" echo     idx.write("--- Verteilung ---\n")
>>"%HELPER%" echo     for i in range(1, MAX_PARTS + 1):
>>"%HELPER%" echo         idx.write("part" + str(i) + ".txt : " + str(files_per_part[i]).rjust(5) + " Dateien, " + str(bytes_per_part[i]).rjust(12) + " bytes\n")
>>"%HELPER%" echo     idx.write("\n--- Dateiliste ---\n")
>>"%HELPER%" echo     for line in index_lines: idx.write(line + "\n")
>>"%HELPER%" echo.
>>"%HELPER%" echo for i in range(1, MAX_PARTS + 1):
>>"%HELPER%" echo     p = os.path.join(OUTDIR, "part" + str(i) + ".txt")
>>"%HELPER%" echo     print("[CHECK] part" + str(i) + ".txt :", os.path.getsize(p), "bytes,", files_per_part[i], "Dateien")
>>"%HELPER%" echo print("[OK] Export fertig.")

if not exist "%HELPER%" (
    echo [FEHLER] Helper-Datei konnte nicht geschrieben werden: %HELPER%
    pause
    exit /b 1
)

echo [4/6] Fuehre Python-Helper aus...
python "%HELPER%" "%ROOT%" "%OUTDIR%"
set "RC=%ERRORLEVEL%"

echo [5/6] Loesche Helper...
del /q "%HELPER%" >nul 2>nul

if not "%RC%"=="0" (
    echo.
    echo [FEHLER] Python-Helper Exit-Code: %RC%
    pause
    exit /b %RC%
)

echo.
echo [6/6] Ergebnis:
dir /b "%OUTDIR%"
echo.
echo Fertig. Dateien liegen unter:
echo    %OUTDIR%\part1.txt
echo    %OUTDIR%\part2.txt
echo    %OUTDIR%\part3.txt
echo    %OUTDIR%\INDEX.txt
echo.
pause
endlocal