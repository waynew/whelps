import re
import sys
import threading
import time

from collections import namedtuple, defaultdict
from datetime import datetime, timedelta


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
            print('\r{} - Task: {}'.format(spent, text), end='')


def store_task(desc, start, end):
    with open('timesheet.txt', 'a') as f:
        fmt = '{:%Y-%m-%d %H:%M:%S} - {:%Y-%m-%d %H:%M:%S}\n\t{}'
        print(fmt.format(start, end, desc), file=f)


def hack_time():
    global text, start
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
                if text == 'q':
                    stopper.set()
                    break
                else:
                    store_task(desc=text, start=start, end=datetime.now())
                    text = ''
                    start = datetime.now()
            elif ch.isspace() or ch.isprintable():
                text += ch
            elif ch == '\x7f':
                spaces = re.sub('[^\t]', ' ', 'xx:xx:xx - Task:'+text)
                print('\r', spaces, end='')
                text = text[:-1]
            else:
                print()
                print(repr(ch))
        except (KeyboardInterrupt, EOFError) as e:
            stopper.set()
            print()
            break
        except:
            stopper.set()
            raise
        finally:
            display_event.set()

    display_thread.join()


def parse_timespan(timespan):
    text_start, _, text_end = timespan.partition(' - ')
    fmt = '%Y-%m-%d %H:%M:%S'
    start = datetime.strptime(text_start, fmt)
    end = datetime.strptime(text_end, fmt)
    return start, end


def report_for_date(date):
    try:
        Span = namedtuple('Span', 'start, end')
        tasks = defaultdict(list)
        with open('timesheet.txt', 'r') as f:
            for timespan, task in zip(f,f):
                try:
                    start, end = parse_timespan(timespan.rstrip())
                except ValueError:
                    print('Unable to parse timespan {!r}, task: {!r}'
                          .format(timespan.strip(), task.strip()))
                else:
                    tasks[task.strip()].append(Span(start=start, end=end))

        for task in sorted(tasks):
            print(task)
            total = timedelta(0)
            for span in tasks[task]:
                total += span.end - span.start
            print('\t{}'.format(total))
    except FileNotFoundError:
        print('Unable to find timesheet.txt, does it exist here?')


def main(args):
    if not args:
        hack_time()
    elif args[0] == 'today':
        report_for_date(datetime.now().date())
    print('Bye!')
            

if __name__ == '__main__':
    main(sys.argv[1:])
