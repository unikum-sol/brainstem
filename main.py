import argparse


def main():
    p = argparse.ArgumentParser()
    # BRAINSTEM_MAIN_CLI_FIX_V1: previously --gui was defined but never
    # actually read anywhere; the admin GUI started by default in every case
    # except --user-gui, which worked but made the --gui flag meaningless and
    # allowed contradictory invocations like "--gui --user-gui" to pass
    # silently. --gui is now the explicit, documented default and mutually
    # exclusive with --user-gui.
    p.add_argument('--gui', action='store_true',
                    help='Startet die vollstaendige Autonomous-Admin-GUI (Standard, auch ohne dieses Flag).')
    p.add_argument('--user-gui', action='store_true',
                    help='Startet die schreibgeschuetzte End-User-Dialog-GUI.')
    p.add_argument('--memory-db', default='ki_memory.sqlite3')
    a = p.parse_args()
    if a.gui and a.user_gui:
        raise SystemExit('--gui und --user-gui schliessen sich gegenseitig aus.')

    # BRAINSTEM_MISSING_BOOTSTRAP_INVOCATION_FIX_V1
    #
    # Root-cause finding (09 September 2026, confirmed via direct code
    # inspection and reproduced with a plain Memory()+AutonomousLoop()
    # sequence matching exactly how this entrypoint used to start either
    # GUI): db_bootstrap.ensure_database_exists() -- the ONLY place in the
    # entire codebase that creates the full central schema (context_
    # hypotheses, internal_learning_gaps, all phaseNa_* tables, and all
    # five shadow-bridge modules) -- was previously NEVER called anywhere
    # in the real startup path. Both gui_app.App() and user_gui.UserApp()
    # only ever construct a plain Memory(...), whose own _init() creates
    # just a small legacy subset of tables (documents, chunks, facts,
    # relations, ontology, questions, conversations, settings, logs,
    # contradictions, clusters, import_state, topic_context). Everything
    # else was only ever created by db_bootstrap.py itself, which was only
    # invoked by systemtest.py and reset_learning.py -- never by the actual
    # program entrypoint. On a freshly created database, this caused real,
    # reproducible core-phase failures on every single learning cycle
    # ("phase6a_replay_control_shadow_latest missing [...]" and
    # "no such table: modern_gap_phase5f_shadow_observation_v2_cycles"),
    # exactly as reported from a real 167,661-chunk production run.
    #
    # Fix: call the full, idempotent central bootstrap here, once, before
    # either GUI is constructed, for both --gui and --user-gui. This uses
    # its own short-lived connection that is opened and closed before
    # Memory() or AutonomousLoop() ever touch the database, so it cannot
    # conflict with anything downstream. ensure_database_exists() is fully
    # idempotent (CREATE TABLE IF NOT EXISTS / ALTER TABLE ADD COLUMN only)
    # and was already verified safe to call repeatedly against the same
    # database with zero side effects on existing data.
    #
    # This is a defense-in-depth fix in addition to (not instead of) making
    # the two specific vulnerable modules self-healing at the call site
    # (see v8_phase6a_replay_control_shadow_release.capture_event and
    # v8_modern_gap_phase5f_shadow_observation_v2_release.record_cycle /
    # record_dual_write), so the schema is correct even if some future code
    # path constructs the GUI classes directly without going through this
    # entrypoint.
    from ki_system.db_bootstrap import ensure_database_exists
    bootstrap_report = ensure_database_exists(a.memory_db)
    if bootstrap_report.get('errors'):
        print('[BRAINSTEM_BOOTSTRAP_WARNING] Nicht-fatale Bootstrap-Fehler beim Start:')
        for phase, err in bootstrap_report['errors']:
            print('   -', phase, ':', err)

    if a.user_gui:
        from ki_system.user_gui import UserApp
        UserApp(a.memory_db).mainloop()
    else:
        from ki_system.gui_app import main as gm
        gm()


if __name__ == '__main__':
    main()
