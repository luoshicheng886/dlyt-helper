#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from PyQt5.QtCore import QSettings, QUrl, QSize, QRect, pyqtSignal, QThread, Qt
from PyQt5.QtGui import QIcon, QFontDatabase, QFont
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtWidgets import (QWidget, QProgressBar, QComboBox, QDialogButtonBox, QDialog, QLineEdit, QDesktopWidget,
                             QPushButton, QHBoxLayout, QVBoxLayout, QApplication, QSizePolicy, QFileDialog, QLabel,
                             QRadioButton, QGroupBox, QCheckBox)
from pytube import YouTube
from pytube.helpers import safe_filename
# noinspection PyUnresolvedReferences
import resource

settings = QSettings('dlyt-helper', QSettings.NativeFormat)
output_path = settings.value('output_path', '')
# mime_type = settings.value('mime_type', '')
# if mime_type == '':
#     mime_type = 'video'
subtype = settings.value('subtype', '')
if subtype == '':
    subtype = 'mp4'
stream_type = settings.value('stream_type', '')
if stream_type == '':
    stream_type = 'all'
dl_cap = settings.value('dl_cap', True, type=bool)
it_list = []
download_ongoing = False


class GetItem(QThread):
    addItem = pyqtSignal(str, str)
    addCaption = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        # self.html = html
        self.url = url
        self.yt = None

    def run(self):
        global it_list
        it_list.clear()
        if 'list' not in self.url:
            self.yt = YouTube(self.url)
            # get stream list
            if stream_type == 'progressive':
                streams = self.yt.streams.filter(progressive=True, subtype=subtype).all()
            elif stream_type == 'adaptive':
                streams = self.yt.streams.filter(adaptive=True, subtype=subtype).all()
            else:
                streams = self.yt.streams.filter(subtype=subtype).all()
            for s in streams:
                # print(s.default_filename, s.itag, s.mime_type, s.resolution, s.fps,
                #       s.video_codec, s.audio_codec, s.filesize)
                if s.video_codec is None:
                    item_txt = 'Format=%-4s abr=%-7s fps=%-3d Size=%-4.3fMB' % (s.mime_type.split('/')[1], s.abr,
                                                                                s.fps, s.filesize / 1024 / 1024)
                else:
                    item_txt = 'Format=%-4s res=%-7s fps=%-3d Size=%-4.3fMB' % (s.mime_type.split('/')[1], s.resolution,
                                                                                s.fps, s.filesize / 1024 / 1024)
                if s.audio_codec is None:
                    codec = 'V'
                    self.addItem.emit(':/video_only-icon', item_txt)
                elif s.video_codec is None:
                    codec = 'A'
                    self.addItem.emit(':/audio_only-icon', item_txt)
                else:
                    codec = 'AV'
                    self.addItem.emit(':/video-icon', item_txt)
                it_list.append(dict(id=s.itag, res=s.abr if s.video_codec is None else s.resolution, codec=codec))
            # get caption list
            for c in self.yt.captions.all():
                self.addCaption.emit(c.name)


# noinspection PyUnusedLocal
class DownLoad(QThread):
    valueChanged = pyqtSignal(float)
    dlCompleted = pyqtSignal()

    def __init__(self, url, idx, cap_idx):
        super().__init__()
        self.cap = cap_idx
        self.url = url
        self.idx = idx
        self.per = 0.0
        self.dlFinished = False

    def run(self):
        yt = YouTube(self.url, on_complete_callback=self.dl_completed, on_progress_callback=self.dl_progress)
        stream = yt.streams.get_by_itag(it_list[self.idx]['id'])
        f_name = stream.title + '-%s' % it_list[self.idx]['res']
        stream.download(output_path=output_path, filename=f_name)
        while not self.dlFinished:
            continue
        # print('%s completed!' % stream.title)
        if dl_cap:
            with open(safe_filename(f_name) + '.%s' % yt.captions.all()[self.cap].code + '.srt', 'w') as fp:
                fp.write(yt.captions.all()[self.cap].generate_srt_captions())

    def dl_progress(self, stream, chunk, handle, rem_bytes):
        # print('%.2f%% completed' % per)
        self.per = (stream.filesize - rem_bytes) / stream.filesize * 100
        self.valueChanged.emit(self.per)

    def dl_completed(self, stream, handle):
        self.dlFinished = True
        self.dlCompleted.emit()


class MainWidget(QWidget):
    def __init__(self, url):
        super().__init__()
        fontDB = QFontDatabase()
        fontDB.addApplicationFont(':/mono-font')
        # fontDB.addApplicationFont(':/Taipei-font')
        screen = QDesktopWidget().screenGeometry()
        self.width, self.height = screen.width(), screen.height()
        self.html = ''
        self.url = url
        self.GI = None
        self.DL = None
        self.web_view = QWebEngineView(self)
        self.web_view.load(QUrl(self.url))
        self.web_view.page().titleChanged.connect(self.get_html)
        btnExit = QPushButton('', self)
        btnExit.setIcon(QIcon(':/exit-icon'))
        btnExit.setIconSize(QSize(32, 32))
        btnExit.setToolTip('Exit')
        btnExit.clicked.connect(QApplication.quit)
        self.btnHome = QPushButton('', self)
        self.btnHome.setIcon(QIcon(':/home-icon'))
        self.btnHome.setIconSize(QSize(32, 32))
        self.btnHome.setToolTip('Home')
        self.btnHome.clicked.connect(self.goHome)
        self.btnBack = QPushButton('', self)
        self.btnBack.setIcon(QIcon(':/go_back-icon'))
        self.btnBack.setIconSize(QSize(32, 32))
        self.btnBack.setToolTip('Backward')
        self.btnBack.clicked.connect(self.goBack)
        self.btnBack.setDisabled(True)
        self.btnNext = QPushButton('', self)
        self.btnNext.setIcon(QIcon(':/go_forward-icon'))
        self.btnNext.setIconSize(QSize(32, 32))
        self.btnNext.setToolTip('Forward')
        self.btnNext.clicked.connect(self.goForward)
        self.btnNext.setDisabled(True)
        self.cmbDownList = QComboBox(self)
        self.cmbDownList.setMinimumHeight(40)
        # font = self.cmbDownList.font()
        font = QFont('Liberation Mono')
        font.setPointSize(14)
        self.cmbDownList.setFont(font)
        self.cmbDownList.setIconSize(QSize(24, 24))
        self.cmbDownList.currentIndexChanged.connect(self.onIndexChanged)
        self.cmbDownList.setToolTip('Select a stream to download')
        self.cmbCapsList = QComboBox(self)
        self.cmbCapsList.setMinimumHeight(40)
        # font = QFont('Taipei Sans TC Beta')
        font = self.cmbCapsList.font()
        font.setPointSize(14)
        self.cmbCapsList.setFont(font)
        self.cmbCapsList.setToolTip('Select a caption/subtitle to download')
        btnSettings = QPushButton('', self)
        btnSettings.setIcon(QIcon(':/settings-icon'))
        btnSettings.setIconSize(QSize(32, 32))
        btnSettings.setToolTip('Settings')
        btnSettings.clicked.connect(self.onSettings)
        self.btnDLoad = QPushButton('', self)
        self.btnDLoad.setIcon(QIcon(':/download-icon'))
        self.btnDLoad.setIconSize(QSize(32, 32))
        self.btnDLoad.setToolTip('Download')
        self.btnDLoad.clicked.connect(self.goDownload)
        self.btnDLoad.setDisabled(True)
        self.progressBar = QProgressBar(self)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)

        hBox1 = QHBoxLayout()
        hBox1.addWidget(btnExit, 0)
        hBox1.addWidget(self.btnHome, 0)
        hBox1.addWidget(self.btnBack, 0)
        hBox1.addWidget(self.btnNext, 0)
        hBox1.addWidget(self.cmbDownList, 1)
        hBox1.addWidget(self.cmbCapsList, 0)
        hBox1.addWidget(btnSettings, 0)
        hBox1.addWidget(self.btnDLoad, 0)
        vBox = QVBoxLayout()
        vBox.addLayout(hBox1)
        vBox.addWidget(self.web_view)
        vBox.addWidget(self.progressBar)
        self.setLayout(vBox)
        self.setWindowTitle('Youtube Download Helper')
        self.setGeometry(QRect((self.width - 760) / 2, (self.height - 550) / 2, 760, 550))
        self.setMinimumSize(QSize(760, 550))

    def store_html(self, html):
        # print('store_html()')
        self.html = html
        if self.web_view.page().action(QWebEnginePage.Back).isEnabled():
            self.btnBack.setEnabled(True)
        else:
            self.btnBack.setDisabled(True)
        if self.web_view.page().action(QWebEnginePage.Forward).isEnabled():
            self.btnNext.setEnabled(True)
        else:
            self.btnNext.setDisabled(True)
        if self.web_view.title() != 'YouTube' and self.web_view.title() != 'https://www.youtube.com':
            # print(self.web_view.title())
            self.btnHome.setEnabled(True)
        else:
            self.btnHome.setDisabled(True)
        self.cmbDownList.clear()
        self.cmbCapsList.clear()
        url = self.web_view.page().url().url()
        if 'video-id' in self.html and '?v=' in url:
            # fp = open(self.web_view.title() + '.html', 'w')
            # fp.write(self.html)
            # fp.close()
            self.GI = GetItem(url)
            self.GI.addItem.connect(self.onAddItem)
            self.GI.addCaption.connect(self.onAddCaption)
            self.GI.finished.connect(self.onAddItemFinished)
            self.GI.start()
        else:
            self.btnDLoad.setDisabled(True)

    def get_html(self):
        # print('get_html')
        self.web_view.page().toHtml(self.store_html)

    def goHome(self):
        self.web_view.setUrl(QUrl(self.url))

    def goBack(self):
        self.web_view.back()

    def goForward(self):
        self.web_view.forward()

    def goDownload(self):
        global download_ongoing
        download_ongoing = True
        self.btnDLoad.setDisabled(True)
        self.progressBar.setValue(0)
        self.DL = DownLoad(self.web_view.page().url().url(), self.cmbDownList.currentIndex(),
                           self.cmbCapsList.currentIndex())
        self.DL.valueChanged.connect(self.onValueChanged)
        self.DL.dlCompleted.connect(self.onDlCompleted)
        self.DL.start()

    def onAddItem(self, icon, item):
        self.cmbDownList.addItem(QIcon(icon), item)

    def onAddCaption(self, cap):
        self.cmbCapsList.addItem(cap)

    def onAddItemFinished(self):
        if not download_ongoing:
            self.btnDLoad.setEnabled(True)

    def onValueChanged(self, per):
        self.progressBar.setValue(round(per))
        # print('%.2f%% completed' % per)

    def onDlCompleted(self):
        global download_ongoing
        download_ongoing = False
        self.btnDLoad.setDisabled(True)
        self.progressBar.setValue(0)

    def onIndexChanged(self):
        if not download_ongoing:
            self.btnDLoad.setEnabled(True)

    def onSettings(self):
        sWnd = SettingsDlg(self.width, self.height)
        sWnd.exec()
        if sWnd.SettingsChanged:
            # print('Settings saved!')
            if self.web_view.title() != 'YouTube' and self.web_view.title() != 'https://www.youtube.com':
                self.web_view.reload()


# noinspection PyMethodMayBeStatic
class SettingsDlg(QDialog):
    def __init__(self, width, height):
        super().__init__()
        self.SettingsChanged = False
        self.setWindowTitle('Settings')
        self.setGeometry(QRect((width - 400) / 2, (height - 200) / 2, 400, 100))
        hBox1 = QHBoxLayout()
        self.lbPath = QLabel(self)
        self.lbPath.setText('File path:')
        self.lnEdit = QLineEdit(self)
        self.lnEdit.setText(output_path)
        self.lnEdit.setToolTip('Edit path')
        self.btnOpen = QPushButton(self)
        self.btnOpen.setIcon(QIcon(':/folder-icon'))
        self.btnOpen.setIconSize(QSize(24, 24))
        self.btnOpen.setToolTip('Choose folder to save downloaded files')
        self.btnOpen.clicked.connect(self.onOpenClicked)
        hBox1.addWidget(self.lbPath, 0)
        hBox1.addWidget(self.lnEdit, 1)
        hBox1.addWidget(self.btnOpen, 0)
        gbStream = QGroupBox(self)
        gbStream.setTitle('Stream type:')
        hBox2 = QHBoxLayout()
        self.btnProgressive = QRadioButton(self)
        self.btnProgressive.setText('progressive')
        self.btnProgressive.setToolTip('Streams with both audio and video tracks')
        self.btnProgressive.toggled.connect(lambda: self.onStreamType(self.btnProgressive.text()))
        self.btnAdaptive = QRadioButton(self)
        self.btnAdaptive.setText('adaptive')
        self.btnAdaptive.setToolTip('Streams with only audio or video track')
        self.btnAdaptive.toggled.connect(lambda: self.onStreamType(self.btnAdaptive.text()))
        self.btnAllStream = QRadioButton(self)
        self.btnAllStream.setText('all')
        self.btnAllStream.setToolTip('Lists all available downloads')
        self.btnAllStream.toggled.connect(lambda: self.onStreamType(self.btnAllStream.text()))
        if stream_type == 'progressive':
            self.btnProgressive.setChecked(True)
        elif stream_type == 'adaptive':
            self.btnAdaptive.setChecked(True)
        else:
            self.btnAllStream.setChecked(True)
        hBox2.addWidget(self.btnProgressive)
        hBox2.addWidget(self.btnAdaptive)
        hBox2.addWidget(self.btnAllStream)
        gbStream.setLayout(hBox2)
        gbSubtype = QGroupBox(self)
        gbSubtype.setTitle('Subtype')
        hBox3 = QHBoxLayout()
        self.btn3Gpp = QRadioButton(self)
        self.btn3Gpp.setText('3gpp')
        self.btn3Gpp.toggled.connect(lambda: self.onSubType(self.btn3Gpp.text()))
        self.btnMp4 = QRadioButton(self)
        self.btnMp4.setText('mp4')
        self.btnMp4.toggled.connect(lambda: self.onSubType(self.btnMp4.text()))
        self.btnWebm = QRadioButton(self)
        self.btnWebm.setText('webm')
        self.btnWebm.toggled.connect(lambda: self.onSubType(self.btnWebm.text()))
        hBox3.addWidget(self.btn3Gpp)
        hBox3.addWidget(self.btnMp4)
        hBox3.addWidget(self.btnWebm)
        gbSubtype.setLayout(hBox3)
        if subtype == '3gpp':
            self.btn3Gpp.setChecked(True)
        if subtype == 'webm':
            self.btnWebm.setChecked(True)
        else:
            self.btnMp4.setChecked(True)
        self.chbDlCap = QCheckBox(self)
        self.chbDlCap.setText('Download a caption if available')
        self.chbDlCap.setChecked(dl_cap)
        vBox = QVBoxLayout()
        vBox.addLayout(hBox1)
        vBox.addWidget(gbStream)
        vBox.addWidget(gbSubtype)
        vBox.addWidget(self.chbDlCap)
        self.btnBox = QDialogButtonBox(self)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btnBox.sizePolicy().hasHeightForWidth())
        self.btnBox.setSizePolicy(sizePolicy)
        self.btnBox.setOrientation(Qt.Horizontal)
        self.btnBox.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.btnBox.accepted.connect(self.onOk)
        self.btnBox.rejected.connect(self.onCancel)
        vBox.addWidget(self.btnBox)
        self.setLayout(vBox)

    def onOpenClicked(self):
        file = str(QFileDialog.getExistingDirectory(self, "Choose Directory"))
        self.lnEdit.setText(file)

    def onStreamType(self, s_type):
        global stream_type
        btn = self.sender()
        if isinstance(btn, QRadioButton) and btn.isChecked():
            stream_type = s_type

    def onSubType(self, sub_type):
        global subtype
        btn = self.sender()
        if isinstance(btn, QRadioButton) and btn.isChecked():
            subtype = sub_type

    def onOk(self):
        global output_path, dl_cap
        output_path = self.lnEdit.text()
        if settings.value('output_path') != output_path:
            settings.setValue('output_path', output_path)
            self.SettingsChanged = True
        if settings.value('stream_type') != stream_type:
            settings.setValue('stream_type', stream_type)
            self.SettingsChanged = True
        if settings.value('subtype') != subtype:
            settings.setValue('subtype', subtype)
            self.SettingsChanged = True
        dl_cap = self.chbDlCap.isChecked()
        if settings.value('dl_cap', type=bool) != dl_cap:
            settings.setValue('dl_cap', 'True' if dl_cap else 'False')
            self.SettingsChanged = True
        self.close()

    def onCancel(self):
        self.close()

    def GetDlgResult(self):
        return self.SettingsChanged


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    w = MainWidget('https://www.youtube.com')
    w.show()
    settings.sync()
    sys.exit(app.exec())
