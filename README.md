# dlyt-helper

A [*pytube*](https://github.com/nficano/pytube) wrapper, YouTube video clips download helper.

# About
Occasionally, I need to watch some YouTube video clips off line. I'd been searching and trying a few browser plugins but
never got a decent one until I found [*pytube*](https://github.com/nficano/pytube). *pytube*, can accomplish almost all
the jobs, is a handy library and command line utility. All the things I've done is only wrapped it in a simple QUI.
Captions are in srt format, which is supported by most video players.

## Prerequisite:
To install the required packages simply use *pip*.
```bash
$ pip install PyQt5
$ pip install PyQtWebEngine
$ pip install pytube
```
Please use *pyrcc5* to compile resources to embed icons and fonts otherwise they won't be seen.
```bash
$ pyrcc5 dlyt-helper.qrc -o resource.py
```