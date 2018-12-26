# bilibili
bilibili space video crawler

Welcome to bilibili downloader
==============================
usage:

general concept of the command line:
>python bilibili.py (mode options) (keywords options) parameters

the concept of the mode options:
1)uod : url->output->download
2)uo  : url->output               (default)
3)od  :      output->download

command line format:
>python bilibili.py [-[u][o][d]] [-k:file] parameter 1 parameter 2 .... parameter n

examples:

1) download all videos from https://space.bilibili.com/30652169/video
>python bilibili.py -uod https://space.bilibili.com/30652169/video
and you can apply keywords options to filter the video titles:
>python bilibili.py -uod -k:keywords.txt https://space.bilibili.com/30652169/video

2) get all video information output to a file from https://space.bilibili.com/30652169/video
>python bilibili.py -uo https://space.bilibili.com/30652169/video
or
>python bilibili.py https://space.bilibili.com/30652169/video
since the -uo is the default mode.
and you can apply keywords options to filter the video titles:
>python bilibili.py -k:keywords.txt https://space.bilibili.com/30652169/video

3) download videos in the specified video information file
>python bilibili.py -od 30652169.csv 33432429.csv
and you can apply keywords options to filter the video titles:
>python bilibili.py -od -k:keywords.txt 30652169.csv 33432429.csv


when proceed downloading tasks, each download of video will be put into a separated process
by executing the following command line:
>python download url, title, index
the url and title are base64 urlsafe encoded, removed ending "="s

acceptable bilibili url : https://space.bilibili.com/30652169/video
the number : 30652169 is called mid and will be used as a folder name to store all related files
we can accept http or https

notice: by default, if you do not specify the keyword file, keyword.txt will be used. if you want to ignore the keywords, use "-k:", which will trigger a warning but no impact and disabled the keywords filter.
