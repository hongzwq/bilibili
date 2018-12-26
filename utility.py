import re
import socket
import time
import math
import datetime
import logging
import logging.handlers
from urllib import request, error

all_loggers = {}


def log(name=None):
    if name is None:
        name = 'not_specified'
    if name in all_loggers:
        g = all_loggers[name]
        return g
    else:
        fmt = logging.Formatter(
            '%(asctime)s %(name)s [%(process)d][%(filename)s]:'
            '[%(levelname)s][%(module)s][%(funcName)s][line:%(lineno)d] %(message)s')
        g = logging.getLogger(name)
        rh = logging.handlers.TimedRotatingFileHandler("{}_log.log".format(name)
                                                       , when='D', interval=1, backupCount=0, encoding='utf-8')
        sh = logging.StreamHandler()
        g.setLevel(logging.DEBUG)  # log everything if a handler want to
        sh.setLevel(logging.INFO)  # only display warning, error and critical on screen
        rh.setLevel(logging.DEBUG)  # log everything in the file
        rh.suffix = '%Y-%m-%d_%H-%M-%S.log'
        rh.setFormatter(fmt)
        sh.setFormatter(fmt)
        g.addHandler(sh)
        g.addHandler(rh)
        all_loggers[name] = g
        return g


logger = log('utility')


def validated_file_name(title):
    rstr = r"[\/\\\:\*\?\"\<\>\|]"
    new_title = re.sub(rstr, "_", title)
    new_title = new_title.replace('utf-8', '')
    new_title = new_title.replace('\r', '')
    new_title = new_title.replace('\n', '')
    new_title = new_title.replace('\t', '')
    return new_title


def progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█'):
    percent = 0.0
    filled_length = 0
    if total > 0:
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end='\r')
    # Print New Line on Complete
    if iteration == total:
        print()


def get_generic_request_headers():
    headers = {
        'User-Agent': r'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      r'Chrome/71.0.3578.98 Safari/537.36',
        'Connection': 'keep-alive',
    }
    return headers


def request_url(url, headers=None, timeout=60):
    logger.debug('requesting {}'.format(url))
    try:
        if headers is None:
            headers = get_generic_request_headers()
        req = request.Request(url, headers=headers)
        res = request.urlopen(req, timeout=timeout)
        return res
    except error.URLError as e:
        logger.error('error: url {} '.format(e.reason))
        return None
    except socket.timeout as e:
        logger.error('error: timeout {}'.format(e))
        return None
    except Exception as e:
        logger.error('error: unknown {}'.format(e))
        return None


def has_keywords(text, words):
    if words is None or len(words) == 0:
        return True
    else:
        for word in words:
            if word in text:
                return True
    return False


def timestamp():
    p1 = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    t = time.time()
    p2 = '{:0>3}'.format(int(math.modf(t)[0]*1000))
    return '{}{}'.format(p1,p2)
