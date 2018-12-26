import sys
import base64
import os

import utility

logger = utility.log('download')

if __name__ == '__main__':
    if len(sys.argv) != 5:
        print('Welcome to download.py')
    else:
        try:
            url = sys.argv[1]
            folder = sys.argv[2]
            title = sys.argv[3]
            index = sys.argv[4]

            url = url + (4 - len(url)) % 4 * '='
            title = title + (4 - len(title)) % 4 * '='

            title = base64.urlsafe_b64decode(title).decode('utf-8')
            url = base64.urlsafe_b64decode(url).decode('utf-8')

            title = utility.validated_file_name(title)

            file = '{}-{}.flv'.format(title, index)
            dn_file = 'downloading_{}'.format(file)

            file = '{}\\{}'.format(folder, file)
            dn_file = '{}\\{}'.format(folder, dn_file)

            headers = utility.get_generic_request_headers()
            headers['Host'] = 'cn-jlcc-gd-acache-02.acgvideo.com'
            headers['Upgrade-Insecure-Requests'] = '1'
            headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
            headers['Accept-Encoding'] = 'gzip, deflate'
            headers['Accept-Language'] = 'en-US,en;q=0.9'

            res = utility.request_url(url, headers)

            length = res.getheader('content-length')
            if length:
                length = int(length)

                if os.path.isfile(file):
                    if os.path.getsize(file) == length:
                        logger.debug('same file {} and same size exist. do not download again'.format(file))
                        print('file {} already exist, cancel download.'.format(file))
                        exit(0)

                block_size = 1024 * 16
                utility.progress_bar(0, length, prefix='Progress:', suffix='Complete', length=50)
                with open(dn_file, "wb") as f:
                    size = 0
                    while True:
                        data = res.read(block_size)
                        if not data:
                            if size == length:
                                break
                            else:
                                raise Exception('{} downloaded size is not same as expected length.'.format(dn_file))
                        f.write(data)
                        size += len(data)
                        if length:
                            utility.progress_bar(size, length, prefix='Progress:', suffix='Complete', length=50)

                if os.path.isfile(file):
                    os.remove(file)
                os.rename(dn_file, file)
                print('downloaded')
            else:
                logger.error('fatal error : unable to get length of video')
                exit(-1)
        except Exception as e:
            logger.error('fatal error : {}'.format(e))
            exit(-1)
