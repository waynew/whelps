'''
Fun with time tracking!
'''
import argparse
import logging
import re
import sys
import threading
import time

from collections import namedtuple, defaultdict
from datetime import datetime, timedelta
from functools import wraps


arg_parser = argparse.ArgumentParser(description=__doc__)
arg_parser.add_argument('--debug', action='store_true')
arg_parser.add_argument('args', nargs='*')

logger = logging.getLogger('whelps.timetracker')


# _find_getch came from this answer on stackoverflow.com
# http://stackoverflow.com/a/21659588/344286
def _find_getch():
    try:
        import termios
    except ImportError:
        logger.debug('Not on POSIX platform, using msvcrt for getch')
        # Non-POSIX. Return msvcrt's (Windows') getch.
        import msvcrt
        @wraps(msvcrt.getch)
        def _getch():
            ch = msvcrt.getch() 
            try:
                ch = ch.decode()
            except UnicodeDecodeError:
                if ch in ('\000', '\xe0'):
                    ctrl = ch
                    ch = msvcrt.getch()
                    logger.info('%r was Windows control character'
                                ' skipping %r', ctrl, ch)
                    ch = ''
                else:
                    logger.exception('Unable to decode chr %r', ch)
                    ch = str(ch)
            return ch
        return _getch

    # POSIX system. Create and return a getch that manipulates the tty.
    import sys, tty
    def _getch():
        logger.debug('Storing off old settings')
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            logger.debug('Old settings have been restored')
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

        if stopper.isSet():
            logger.debug('Stopping thread...')
        else:
            print('\r{} - Task: {}'.format(spent, text), end='')


def store_task(desc, start, end):
    logger.info('Storing task %r-%r: %r', start, end, desc)
    with open('timesheet.txt', 'a') as f:
        fmt = '{:%Y-%m-%d %H:%M:%S} - {:%Y-%m-%d %H:%M:%S}\n\t{}'
        print(fmt.format(start, end, desc), file=f)


def hack_time():
    global text, start
    logger.debug('Hacking time... well, to record time spent hacking')
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
            logger.debug('Read character %r', ch)
            if ch == '\r':
                print()
                if text == 'q':
                    logger.debug('Quitting...')
                    stopper.set()
                    break
                else:
                    store_task(desc=text, start=start, end=datetime.now())
                    text = ''
                    start = datetime.now()
            elif ch.isspace() or ch.isprintable():
                text += ch
            elif ch in ('\x7f', '\x08'):
                spaces = re.sub('[^\t]', ' ', 'xx:xx:xx - Task:'+text)
                print('\r', spaces, end='')
                text = text[:-1]
            elif ch == '\x1b':
                data = [getch(), getch()]
                logger.info('Got linux control character %r, eating'
                             ' two bytes %r', ch, data)
            else:
                logger.warning('Unknown char: %r', ch)
        except (KeyboardInterrupt, EOFError) as e:
            stopper.set()
            print()
            break
        except:
            stopper.set()
            raise
        finally:
            display_event.set()

    logger.debug('Waiting for display thread to join...')
    display_thread.join()
    logger.debug('Display thread absorbed')


def pomodoro(days, hours, minutes, seconds):
    global text, start
    logger.debug('Running pomodoro interval for %dd%dh%dm%ds',
                 days, hours, minutes, seconds)
    stopper = threading.Event()
    display_event = threading.Event()
    display_thread = threading.Thread(
        target=display,
        args=(stopper, display_event),
    )
    display_thread.start()
    display_event.set()

    start = datetime.now()
    tomato_length = timedelta(days=days, hours=hours, minutes=minutes,
                              seconds=seconds)
    end = start+tomato_length

    ch = ''
    while True:
        try:
            ch = getch()
            if ch == 'q':
                stopper.set()
                print()
                break
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
    logger.debug('Parsing %r', timespan)
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
                    if start.date() <= date <= end.date():
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
    if not args.args:
        hack_time()
    else:
        # TODO: Fix this pattern -W. Werner, 2016-11-04
        pattern = r'(?=.*[smhd])(?:(\d+)d)?\s*(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+)s)?'
        #match = re.match(pattern, args.args)
        match = None
        if match is None:
            if args.args == 'today':
                report_for_date(datetime.now().date())
            else:
                print('Unknown argument {!r}'.format(args.args))
        else:
            days, hours, minutes, seconds = (int(val or 0) for val in match.groups())
            pomodoro(days=days, hours=hours, minutes=minutes, seconds=seconds)
    print('Bye!')
            

if __name__ == '__main__':
    args = arg_parser.parse_args()
    args.args = ' '.join(args.args)
    if args.debug:
        log_filename = 'timetracker.log'
        h = logging.FileHandler(log_filename)
        for thing in (logger, h):
            thing.setLevel(logging.DEBUG)
        logger.addHandler(h)
        logger.addHandler(logging.StreamHandler())
        for h in logger.handlers:
            h.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(threadName)s:%(message)s'))
        logger.info('Logging information to %s', log_filename)
        logger.handlers.pop()
    logger.debug('Args %r', args)
    main(args)
    logger.debug('Shut down')
