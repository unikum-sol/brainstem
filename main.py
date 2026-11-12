import argparse


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--gui', action='store_true',
                    help='Startet die vollstaendige Autonomous-Admin-GUI (Standard, auch ohne dieses Flag).')
    p.add_argument('--user-gui', action='store_true',
                    help='Startet die schreibgeschuetzte End-User-Dialog-GUI.')
    p.add_argument('--memory-db', default='ki_memory.sqlite3')
    a = p.parse_args()
    if a.gui and a.user_gui:
        raise SystemExit('--gui und --user-gui schliessen sich gegenseitig aus.')

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
