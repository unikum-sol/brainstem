import argparse
def main():
    p=argparse.ArgumentParser(); p.add_argument('--gui',action='store_true'); p.add_argument('--user-gui',action='store_true'); p.add_argument('--memory-db',default='ki_memory.sqlite3'); a=p.parse_args()
    if a.user_gui:
        from ki_system.user_gui import UserApp; UserApp(a.memory_db).mainloop()
    else:
        from ki_system.gui_app import main as gm; gm()
if __name__=='__main__': main()
