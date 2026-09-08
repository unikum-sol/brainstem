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
    if a.user_gui:
        from ki_system.user_gui import UserApp
        UserApp(a.memory_db).mainloop()
    else:
        from ki_system.gui_app import main as gm
        gm()


if __name__ == '__main__':
    main()
