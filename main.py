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
        # BRAINSTEM_FATAL_STARTUP_ABORT_FIX_V1
        #
        # Root cause: v8_phase_registry.load_all() already computed an
        # explicit report["fatal"] flag whenever a required (non-dead_code)
        # phase module failed to load, and report["self_check"]["ok"]
        # already reflects the project's own established definition of a
        # correctly wired phase chain (cycle() resolves to Phase 7d's
        # managed_cycle, fact_promotion stays disabled, and there are no
        # load errors). However, nothing anywhere in the actual program
        # entrypoint ever checked either of these -- the admin GUI started
        # normally regardless of whether the underlying autonomous-learning
        # phase chain was fully, partially, or not at all wired up.
        # autonomous.py's own module-level exception handler additionally
        # only ever printed a crash from load_all() itself and continued.
        # The net effect: a genuinely broken phase chain (e.g. from a
        # missing/renamed module, a real Python error in a phase file, or a
        # dependency import failure) could silently fall back to whatever
        # partial AutonomousLoop.cycle chain happened to remain patched in,
        # and the admin GUI would start up looking completely normal.
        #
        # Fix: import gui_app first (its own module-level
        # "from ki_system.autonomous import AutonomousLoop" already
        # triggers phase_registry.load_all() exactly once, before this
        # point), then explicitly check the resulting load report via the
        # new autonomous.get_load_report() accessor. Only the admin GUI
        # path is gated here: user_gui.py (see above) never imports
        # ki_system.autonomous at all, since the read-only dialogue GUI
        # does not run learning cycles and does not depend on the phase
        # chain being wired at all -- gating it on this check would be
        # both unnecessary and would force an otherwise-avoidable import
        # of the entire phase chain for a mode that never uses it.
        from ki_system.gui_app import main as gm
        from ki_system.autonomous import get_load_report
        load_report = get_load_report()
        if load_report.get('fatal'):
            print('[BRAINSTEM_FATAL] Ein oder mehrere erforderliche Phasen-Module konnten')
            print('nicht geladen werden. Die Lern-Phasenkette ist unvollstaendig verdrahtet.')
            print('Start der Admin-GUI wird verweigert, um einen degradierten, nur teilweise')
            print('verdrahteten Autonomes-Lernen-Betrieb zu vermeiden.')
            for failed_label, exc_repr in load_report.get('errors', []):
                print('   -', failed_label, ':', exc_repr)
            raise SystemExit(1)
        gm(a.memory_db)


if __name__ == '__main__':
    main()
