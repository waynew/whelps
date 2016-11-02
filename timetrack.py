import sys
import time
import threading

from datetime import datetime


# _find_getch came from this answer on stackoverflow.com
# http://stackoverflow.com/a/21659588/344286
def _find_getch():
    try:
        import termios
    except ImportError:
        # Non-POSIX. Return msvcrt's (Windows') getch.
        import msvcrt
        return msvcrt.getch

    # POSIX system. Create and return a getch that manipulates the tty.
    import sys, tty
    def _getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        if ord(ch) == 3:
            raise KeyboardInterrupt('^C entered')
        if ord(ch) == 4:
            raise EOFError('EOF entered')
        return ch

    return _getch

getch = _find_getch()

start = datetime.now()
text = ''

def display(stopper, display_event):
    while not stopper.isSet():
        display_event.wait(timeout=1)
        display_event.clear()
        time_spent = datetime.now() - start
        s = int(time_spent.total_seconds())
        hours = s // 3600
        s = s - (hours*3600)
        minutes = s // 60
        seconds = s - (minutes*60)
        spent = '{:0>2}:{:0>2}:{:0>2}'.format(hours, minutes, seconds)

        if not stopper.isSet():
            print('\r{} - Choice: {}'.format(spent, text), end='')


def main():
    global text
    stopper = threading.Event()
    display_event = threading.Event()
    display_thread = threading.Thread(
        target=display,
        args=(stopper, display_event),
    )
    display_thread.start()
    display_event.set()

    ch = ''
    while True:
        try:
            ch = getch()
            if ch == '\r':
                print()
                print(text)
                print()
                if text == 'q':
                    stopper.set()
                    break
                else:
                    text = ''
            elif ch.isspace() or ch.isalnum():
                text += ch
            elif ch == '\x7f':
                text = text[:-1]
                print('\r', ' '*len('xx:xx:xx - Task:'+text), end='')
            else:
                print()
                print(repr(ch))
                print()
        except:
            stopper.set()
            raise
        finally:
            display_event.set()

    display_thread.join()
    print('\nBye!')
            

if __name__ == '__main__':
    main()
