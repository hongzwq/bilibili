import os
import re
import csv
import sys
import json
import zlib
import base64
import platform
import threading
import subprocess

import utility

logger = utility.log('bilibili')


def parse_command_line():
    option_mode = 'uo'  # default mode (url->output)
    option_keywords = 'keywords.txt'  # default keyword file
    parameters = []
    if len(sys.argv) == 1:
        option_mode = 'h'  # help mode, print the help.txt
    else:
        for arg in sys.argv[1:]:
            raw = arg.strip()
            if raw.startswith('-'):  # this is an option item
                option = arg[1:].strip()
                parts = option.split(':')
                if len(parts) == 1:
                    option = option.lower()
                    if option in ['uo', 'od', 'uod']:
                        option_mode = option
                    else:
                        logger.error('not supported option {}'.format(arg))
                        option_mode = None
                elif len(parts) == 2:
                    if parts[0].strip().lower() == 'k':
                        option_keywords = parts[1].strip()
                    else:
                        logger.error('not supported option {}'.format(arg))
                        option_mode = None
                        option_keywords = None
                else:
                    logger.error('not supported option {}'.format(arg))
                    option_mode = None
            else:
                parameters.append(arg.strip())
    return option_mode, option_keywords, parameters


def check_urls(args):
    for arg in args:
        match = re.search('https*://space.bilibili.com/[0-9]+/video', arg)
        if not match:
            logger.warning('{} is not a supported bilibili url'
                         'please use url like https://space.bilibili.com/30652169/video'.format(arg))
            return False
    return True


def get_topics(param_mid, param_page_no=1, words=None, param_page_size=100):
    adr = ("https://space.bilibili.com/ajax/member/getSubmitVideos?mid={}&pagesize={}&tid=0&page={"
           "}&keyword=&order=pubdate").format(param_mid, param_page_size, param_page_no)
    res = utility.request_url(adr)
    if res is None:
        return None
    else:
        try:
            result = []
            content = res.read()
            content = content.decode('utf-8')
            data = json.loads(content)
            status = data['status']
            if status:
                data = data['data']
                # tlist = data['tlist'] #do not need so far
                vlist = data['vlist']
                for item in vlist:
                    title = item['title']
                    if utility.has_keywords(title, words):
                        result.append(
                            dict(pages=data['pages'], count=data['count'], ref=adr, mid=param_mid, aid=item['aid'],
                                 title=title))
                return result
            else:
                logger.error('error : failed to get video topics {} from {}'.format(data['data'], adr))
                return None
        except Exception as e:
            logger.error('error : failed to get video topics {} from {}'.format(e, adr))
            return None


def get_cid(param_aid, param_ref, param_retry=0):
    headers = utility.get_generic_request_headers()
    headers['Referer'] = param_ref
    headers['"Accept-Encoding"'] = 'gzip, deflate'
    adr = "https://www.bilibili.com/video/av{}".format(param_aid)
    res = utility.request_url(adr, headers)
    if res is None:
        return None
    else:
        try:
            content = res.read()
            gzipped = res.headers.get('Content-Encoding')
            if gzipped:
                content = zlib.decompress(content, 16 + zlib.MAX_WBITS)
                content = content.decode('utf-8')
            index1, index2, index3 = 0, 0, 0
            index1 = content.find('window.__INITIAL_STATE__')
            if index1 > 0:
                index2 = content.find("\"cid\":", index1)
            if index2 > 0:
                index3 = content.find(",", index2)
            if 0 < index1 < index2 < index3:
                cid_result = content[index2 + 6: index3]
                return cid_result
            else:
                if param_retry < 3:
                    logger.debug('failed to get cid. retry {}'.format(adr))
                    return get_cid(param_aid, param_ref, param_retry + 1)
                else:
                    logger.error('error : failed to find cid from {}, tried ({},{},{})'
                                 .format(adr, index1, index2, index3))
                    return None
        except Exception as e:
            logger.error('error : failed to find cid from {}. {}'.format(adr, e))
            return None


def get_videos(param_mid, param_aid, param_cid, param_title):
    adr = "https://www.kanbilibili.com/api/video/{}/download?cid={}&quality=80&page=1".format(param_aid, param_cid)
    res = utility.request_url(adr)
    if res is None:
        return None
    else:
        try:
            content = res.read()
            content = content.decode('utf-8')
            data = json.loads(content)
            data = data['data']
            iserror = (data['result'] == 'error')
            if not iserror:
                durl = data['durl']
                index = 0
                results = []
                for item in durl:
                    index = index + 1
                    results.append(dict(mid=param_mid, aid=param_aid, cid=param_cid,
                                        url=item['url'], title=param_title, index=index))
                return results
            else:
                logger.error('error : return error json {}'.format(data['message']))
                return None
        except Exception as e:
            logger.error('error : failed to get video info {}'.format(e))
            return None


def load_topics(urls, words=None):
    if not check_urls(urls):
        exit(-1)
    else:
        results = []
        idx = 0
        for url in urls:
            idx += 1
            print('processing url(s) {}/{} : {}'.format(idx, len(urls), url))
            mid = (url.split('/'))[3]
            if len(mid) == 0:
                logger.warning('error : failed to locate mid')
            else:
                print('loading topics primary data ...')
                page = 1
                topics = get_topics(mid, page)
                if topics is not None:
                    pages = topics[0]['pages']
                    count = topics[0]['count']

                    print('{} topics in {} pages to be loaded'.format(count, pages))
                    # reload and apply keywords
                    topics = []
                    utility.progress_bar(0, pages, prefix='Progress:', suffix='Complete', length=50)
                    page = 0
                    while page < pages:
                        page += 1
                        new_page_topics = get_topics(mid, page, words)
                        if new_page_topics is not None:
                            topics.extend(new_page_topics)
                        utility.progress_bar(page, pages, prefix='Progress:', suffix='Complete', length=50)
                    if len(topics) > 0:
                        print('loading cid for {} topic(s)'.format(len(topics)))
                        step = 0
                        utility.progress_bar(step, len(topics), prefix='Progress:', suffix='Complete', length=50)
                        for topic in topics:
                            step += 1
                            ref = topic['ref']
                            title = topic['title']
                            aid = topic['aid']
                            cid = get_cid(aid, ref)
                            if cid is not None:
                                results.append(dict(mid=mid, aid=aid, cid=cid, title=title, url=url))
                            else:
                                # failed to get cid, save to error file
                                save_failed_download(dict(mid=mid, aid=aid,cid='', title=title, url=url))
                            utility.progress_bar(step, len(topics), prefix='Progress:', suffix='Complete', length=50)
        print('{} topics loaded.'.format(len(results)))
        return results


def save_outputs(topics):
    groups = {}
    for topic in topics:
        mid = topic['mid']
        if mid not in groups:
            groups[mid] = []
        groups[mid].append(topic)
    print('saving {} topics(s) to {} file(s) ...'.format(len(topics), len(groups.keys())))
    results = []
    try:
        headers = ['mid', 'aid', 'cid', 'title', 'url']
        for k, v in groups.items():
            if not os.path.exists(k):
                os.makedirs(k)
                logger.debug('folder {} created'.format(k))
            fn = '{0}\\{0}.csv'.format(k)
            print('saving {} topics to {} ...'.format(len(v), fn))
            with open(fn, 'w', newline='', encoding='utf-8')as f:
                writer = csv.DictWriter(f, headers)
                writer.writeheader()
                writer.writerows(v)
            print('{} topics saved in {}'.format(len(v), fn))
            results.append(fn)
    except Exception as e:
        logger.error('error : failed to save topics. {}'.format(e))
    return results


def load_outputs(files, words):
    print('loading {} file(s) ...'.format(len(files)))
    topics = []
    try:
        for fn in files:
            print('loading topics from {}'.format(fn))
            if os.path.isfile(fn):
                with open(fn, 'r', encoding="utf-8") as f:
                    reader = csv.reader(f)
                    headers = next(reader)
                    if not headers == ['mid', 'aid', 'cid', 'title', 'url']:
                        logger.error('file headers {} is not acceptable'.format(fn))
                        continue
                    reader = csv.DictReader(f, fieldnames=headers)
                    for row in reader:
                        title = row['title']
                        if utility.has_keywords(title, words):
                            topics.append(row)
            else:
                logger.error('file {} is not found'.format(fn))
            if len(topics) > 0:
                for topic in topics:
                    # check if the cid is not valid
                    aid = topic['aid']
                    cid = topic['cid']
                    ref = topic['url']
                    title = topic['title']
                    if len(cid.strip()) == 0:
                        logger.debug('missing cid, loading cid with aid={} ref={}'.format(aid, ref))
                        print('fetching missing cid for {}'.format(title))
                        cid = get_cid(aid, ref)
                        if cid is not None:
                            topic[cid] = cid
    except Exception as e:
        logger.error('error : failed to load topics'.format(e))
    print('{} topics(s) loaded ...'.format(len(topics)))
    return topics


def process_download(size=20):
    global all_topics  # depends on global all_topics, all_downloads
    print('{} topics(s) to download by max {} parallelled processes ...'.format(len(all_topics), size, ))
    download_tasks(size)


def download_tasks(size):
    global all_topics
    cnt_waiting, cnt_doing, cnt_completed, cnt_terminated, cnt_killed = update_download_tasks_status()
    cnt_topic_waiting, cnt_topic_completed, cnt_topic_downloading, cnt_topic_failed = count_topic_download_status()

    free_space = size - cnt_doing - cnt_waiting
    cnt_topic_remains = 0
    cnt = 0
    for topic in all_topics:
        if cnt_topic_completed + cnt_topic_failed < len(all_topics):  # to avoid double progress bar
            utility.progress_bar(cnt_topic_completed + cnt_topic_failed,
                                 len(all_topics), prefix='Scanning:', suffix='Complete', length=50)
        if 'download' not in topic:
            if free_space > 0:
                cnt += 1
                utility.progress_bar(cnt_topic_completed + cnt_topic_failed, len(all_topics),
                                     prefix='Loading :', suffix='{}/{}     '.format(cnt, free_space), length=50)
                mid = topic['mid']
                aid = topic['aid']
                cid = topic['cid']
                title = topic['title']
                videos = get_videos(mid, aid, cid, title)
                if videos is None:
                    topic['url'] = ''
                    save_failed_download(topic)
                else:
                    for video in videos:
                        video['status'] = 0  # waiting to start
                        video['process'] = None
                    all_downloads.extend(videos)
                    topic['download'] = videos
                    free_space -= len(videos)

            else:
                cnt_topic_remains += 1

    trigger_downloads(size)

    cnt_waiting, cnt_doing, cnt_completed, cnt_terminated, cnt_killed = update_download_tasks_status()
    cnt_topic_waiting, cnt_topic_completed, cnt_topic_downloading, cnt_topic_failed = count_topic_download_status()

    utility.progress_bar(cnt_topic_completed + cnt_topic_failed,
                         len(all_topics), prefix='Progress:', suffix='Complete', length=50)

    if cnt_topic_remains > 0 or cnt_waiting > 0 or cnt_doing > 0:
        timer = threading.Timer(2.0, download_tasks, [size])
        timer.start()


def trigger_downloads(size):
    global all_downloads, startupinfo
    cnt_waiting, cnt_doing, cnt_completed, cnt_terminated, cnt_killed = update_download_tasks_status()
    free_space = size - cnt_doing

    if free_space > 0:
        for download in all_downloads:
            if free_space <= 0:
                break
            if download['status'] == 0:
                try:
                    adr = download['url']
                    folder = download['mid']
                    title = download['title']
                    index = str(download['index'])
                    adr = base64.urlsafe_b64encode(bytes(adr, 'utf-8')).decode('utf-8').rstrip('=')
                    title = base64.urlsafe_b64encode(bytes(title, 'utf-8')).decode('utf-8').rstrip('=')
                    command = ["python", "download.py", "{}".format(adr), folder, "{}".format(title), index]
                    logger.debug('downloading command {}'.format(command))
                    download['process'] = subprocess.Popen(command,
                                                           startupinfo=startupinfo,
                                                           creationflags=subprocess.CREATE_NEW_CONSOLE)
                    download['status'] = 1
                    free_space -= 1
                except Exception as e:
                    logger.error('download error {}'.format(e))
                    download['process'] = None
                    download['status'] = 0  # try next time


def update_download_tasks_status():
    global all_downloads
    cnt_waiting, cnt_doing, cnt_completed, cnt_terminated, cnt_killed = 0, 0, 0, 0, 0
    for download in all_downloads:
        proc = download['process']
        if proc is not None:
            if proc.poll() is None:  # downloading
                download['status'] = 1
                cnt_doing += 1
            elif proc.poll() == 0:  # download complete normally
                download['status'] = 2
                cnt_completed += 1
            elif proc.poll() < 0:  # killed
                download['status'] = -1
                cnt_killed += 1
                if 'failed_logged' not in download:
                    save_failed_download(download)
                    logger.warning('error : downloading file {} was killed'.format(download['title']))
                    download['failed_logged'] = True
            else:
                download['status'] = -2  # not sure what is happening
                cnt_terminated += 1
                if 'failed_logged' not in download:
                    save_failed_download(download)
                    logger.warning('error : downloading file {} was terminated'.format(download['title']))
                    download['failed_logged'] = True
        else:
            download['status'] = 0  # waiting
            cnt_waiting += 1
    return cnt_waiting, cnt_doing, cnt_completed, cnt_terminated, cnt_killed


def count_topic_download_status():
    global all_topics
    cnt_waiting, cnt_completed, cnt_downloading, cnt_failed = 0, 0, 0, 0
    for topic in all_topics:
        if 'download' in topic:
            status = []
            for download in topic['download']:
                status.append(download['status'])
            if len(status) > 0:
                status.sort()
                if status[0] == 0 and status[-1] == 0:  # every download is waiting
                    cnt_waiting += 1
                elif status[0] < 0:
                    cnt_failed += 1
                elif sum(status) / len(status) == 2:  # everything completed
                    cnt_completed += 1
                else:
                    cnt_downloading += 1
        else:
            cnt_waiting += 1
    return cnt_waiting, cnt_completed, cnt_downloading, cnt_failed


def load_keywords(kwfn):
    words = []
    if os.path.isfile(kwfn):
        with open(kwfn, 'r', encoding="utf_8_sig") as f:  # UTF-8 BOM , to remove heading \ufeff
            for line in f:
                word = line.strip()
                if len(word) > 0:
                    words.append(word)
    else:
        logger.warning('keywords file {} not found'.format(kwfn))
    return words


def save_failed_download(dn):
    global runid
    try:
        headers = ['mid', 'aid', 'cid', 'title', 'url']
        fn = '{0}.csv'.format(runid)
        print('saving failed topic to {} ...'.format(fn))
        exist = os.path.isfile(fn)
        with open(fn, 'a', newline='', encoding='utf-8')as f:
            writer = csv.DictWriter(f, headers)
            if not exist:
                writer.writeheader()
            writer.writerow(dict(mid=dn['mid'], aid=dn['aid'], cid=dn['cid'], title=dn['title'], url=dn['url']))
        print('failed topic saved in {}'.format(fn))
    except Exception as e:
        logger.error('error : failed to save topics. {}'.format(e))


if __name__ == '__main__':
    runid = utility.timestamp()
    md, kw, params = parse_command_line()
    if md is None:
        exit(-1)
    if md == 'h':
        if os.path.isfile('help.txt'):
            if 'Darwin' in platform.system():
                os.system('cat help.txt')
            if 'Windows' in platform.system():
                os.system('type help.txt')
        exit(0)

    all_topics, all_files, all_downloads = [], [], []

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE

    keywords = []
    if kw is not None:
        keywords = load_keywords(kw)
        if keywords is not None:
            print('keywords={}'.format(keywords))

    if md == 'uo':
        all_topics = load_topics(params, keywords)
        all_files = save_outputs(all_topics)
    if md == 'od':
        all_topics = load_outputs(params, keywords)
        process_download()
    if md == 'uod':
        all_topics = load_topics(params, keywords)
        all_files = save_outputs(all_topics)
        process_download()
