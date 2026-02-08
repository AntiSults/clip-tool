import subprocess
import os
import imageio_ffmpeg
import datetime

from PySide6.QtMultimedia import (QAudioOutput, QMediaDevices, QMediaPlayer, QtAudio)
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog,
                               QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
                               QSizePolicy, QSlider, QVBoxLayout, QWidget, QToolButton, QStyle,
                               QSlider, QStyle, QStyleOptionSlider, QDialogButtonBox, QFormLayout, QCheckBox)
from PySide6.QtGui import QKeySequence, QShortcut, QPainter, QPen, QIcon
from PySide6.QtCore import QTime, Qt, Signal, Slot, QUrl

COLOR_GREEN = "#076600"
COLOR_RED = "#660003"
ICON = "assets/icon/icon.ico"

class ExportDialog(QDialog):
    def __init__(self, default_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export clip")

        self.nameEdit = QLineEdit(default_name)
        self.deleteCheck = QCheckBox("Delete original file after successful export")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout(self)
        form.addRow("Output filename:", self.nameEdit)
        form.addRow("", self.deleteCheck)
        form.addRow(buttons)

    def filename(self) -> str:
        return self.nameEdit.text().strip()

    def delete_original(self) -> bool:
        return self.deleteCheck.isChecked()
    
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt

class ConfirmDeleteDialog(QDialog):
    def __init__(self, parent=None, filename=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Deletion")
        self.setModal(True)

        text = "Are you sure you want to delete this clip?"
        if filename:
            text += f"\n\n{filename}"

        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)

        btn_yes = QPushButton("Delete")
        btn_no = QPushButton("Cancel")

        btn_yes.clicked.connect(self.accept)
        btn_no.clicked.connect(self.reject)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_no)
        btn_layout.addWidget(btn_yes)

        layout = QVBoxLayout(self)
        layout.addWidget(label)
        layout.addLayout(btn_layout)

class MarkedSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._start = None  # int (ms) or None
        self._end = None    # int (ms) or None

    def removeCutMarks(self):
        self._start = None
        self._end = None
        self.update()

    def setCutMarks(self, start: bool, var):
        if start:
            self._start = var 
        else: 
            self._end = var
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        if self.orientation() != Qt.Orientation.Horizontal:
            return

        opt = QStyleOptionSlider()
        self.initStyleOption(opt)

        groove = self.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self)

        painter = QPainter(self)
        pen = QPen(Qt.GlobalColor.yellow)
        pen.setWidth(2)
        painter.setPen(pen)

        def draw_mark(value):
            if value is None:
                return
            v = int(value)
            if self.maximum() == self.minimum():
                return
            # Map value -> pixel position along the groove, using Qt's helper
            x = QStyle.sliderPositionFromValue(self.minimum(), self.maximum(), v, groove.width())
            x = groove.left() + x
            painter.drawLine(x, groove.top(), x, groove.bottom())

        draw_mark(self._start)
        draw_mark(self._end)

class PlayerControls(QWidget):
    play = Signal()
    pause = Signal()
    cutPhase = Signal()
    cut = Signal()
    changeVolume = Signal(float)
    
    def __init__(self, parent = None):
        super().__init__(parent)

        # Play button
        style = self.style()
        self.tempBool = True
        self.m_playButton = QToolButton(self)
        self.m_playButton.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.m_playButton.setToolTip("Play")
        self.m_playButton.clicked.connect(self.playClicked)

        # Pause button
        self.m_pauseButton = QToolButton(self)
        self.m_pauseButton.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        self.m_pauseButton.setToolTip("Pause")
        self.m_pauseButton.clicked.connect(self.pauseClicked)

        # Volume slider
        self.m_volumeSlider = QSlider(Qt.Orientation.Horizontal, self)
        self.m_volumeSlider.setRange(0, 100)
        self.m_volumeSlider.setValue(100)
        ##sp = self.m_volumeSlider.sizePolicy()
        ##sp.setHorizontalPolicy(QSizePolicy.Policy.MinimumExpanding)
        self.m_volumeSlider.valueChanged.connect(self.onVolumeSliderValueChanged)
        self.m_volumeSlider.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        
        self.m_cutPhaseButton = QPushButton("Swap Marker[s]", self)
        self.m_cutPhaseButton.clicked.connect(self.cutPhaseSwap)
        self.m_cutPhaseButton.setStyleSheet(f"QPushButton {{ background-color: {COLOR_GREEN}; }}")
        self.m_cutPosButton = QPushButton("Set Cut Marker[c]", self)
        self.m_cutPosButton.clicked.connect(self.cutPosClicked)
        ##self.m_endPosButton = QPushButton("End", self)
        ##self.m_endPosButton.clicked.connect(self.endPosClicked)

        # Controls widget layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.m_pauseButton)
        layout.addWidget(self.m_playButton)
        layout.addWidget(self.m_volumeSlider)
        layout.addWidget(self.m_cutPhaseButton)
        layout.addWidget(self.m_cutPosButton)

    def volume(self):
        linearVolume = QtAudio.convertVolume(self.m_volumeSlider.value() / 100.0,
                                             QtAudio.VolumeScale.LogarithmicVolumeScale,
                                             QtAudio.VolumeScale.LinearVolumeScale)
        return linearVolume

    @Slot()
    def onVolumeSliderValueChanged(self):
        self.changeVolume.emit(self.volume())

    @Slot()
    def cutPhaseSwap(self):
        self.cutPhase.emit()

    def swapCutText(self):
        print(f"Tempbool: {getattr(self, "tempBool")}")    
        if getattr(self, "tempBool"):
            self.m_cutPhaseButton.setText("Swap (End)[s]")
            self.m_cutPhaseButton.setStyleSheet(f"QPushButton {{ background-color: {COLOR_RED}; }}")
            setattr(self, "tempBool", False)
        else:
            self.m_cutPhaseButton.setText("Swap (Start)[s]")
            setattr(self, "tempBool", True)
            self.m_cutPhaseButton.setStyleSheet(f"QPushButton {{ background-color: {COLOR_GREEN}; }}")

    @Slot()
    def cutPosClicked(self):
        self.cut.emit()



    @Slot()
    def playClicked(self):
        self.play.emit()

    @Slot()
    def pauseClicked(self):
        self.pause.emit()

class Player(QWidget):
    changeVolume = Signal(float)
    def __init__(self, /, parent = None):
        super().__init__(parent)

        style = self.style()
        self.loadCutVideo = False
        self.setWindowTitle("Clip Tool")
        self.setWindowIcon(QIcon(ICON))
        self.m_mediaDevices = QMediaDevices()
        self.m_player = QMediaPlayer(self)
        self.m_audioOutput = QAudioOutput(self)
        self.m_player.setAudioOutput(self.m_audioOutput)
        
        # Layout setup
        mainLayout = QVBoxLayout(self)
        firstRow = QHBoxLayout()
        bottomRow = QHBoxLayout()

        # DEBUG
        self.m_player.mediaStatusChanged.connect(lambda s: print("status:", s))
        self.m_player.playbackStateChanged.connect(lambda s: print("state:", s))
        self.m_player.hasVideoChanged.connect(lambda v: print("hasVideo:", v))
        self.m_player.sourceChanged.connect(lambda u: print("source:", u.toString()))       

        

        ##self.m_player.hasVideoChanged.connect(self.VideoAvailableChanged)
        self.m_player.errorChanged.connect(self.displayErrorMessage)

        # File opening widgets
        self.openButton = QPushButton("Open File", self)
        self.openButton.clicked.connect(self.open)
        self.fileLabel = QLabel("Open a file...")
        # Delete button
        self.m_deleteButton = QToolButton(self)
        self.m_deleteButton.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_BrowserStop))
        self.m_deleteButton.setToolTip("delete")
        self.m_deleteButton.clicked.connect(self.clickDelete)
        #Confirm button
        self.m_confirmPosButton = QPushButton("Confirm cut",self)
        self.m_confirmPosButton.clicked.connect(self.confirmCut)

        firstRow.addWidget(self.openButton)
        firstRow.addWidget(self.fileLabel)
        firstRow.addWidget(self.m_deleteButton)
        firstRow.addWidget(self.m_confirmPosButton)

        mainLayout.addLayout(firstRow)

        #Video player widget
        self.m_videoWidget = QVideoWidget(self)
        available_geometry = self.screen().availableGeometry()
        self.m_videoWidget.setMinimumSize(available_geometry.width() / 2, available_geometry.height() / 3)
        self.m_player.setVideoOutput(self.m_videoWidget)

        mainLayout.addWidget(self.m_videoWidget, stretch=1)

        # duration slider and label
        sliderLayout = QHBoxLayout()

        #Timeline (need 2 functions)
        self.m_player.durationChanged.connect(self.durationChanged)
        self.m_player.positionChanged.connect(self.positionChanged)

        self.m_slider = MarkedSlider(Qt.Orientation.Horizontal, self)
        self.m_slider.adjustSize()
        self.m_slider.setRange(0, self.m_player.duration())
        self.m_slider.sliderMoved.connect(self.seek)
        sliderLayout.addWidget(self.m_slider, stretch=1)

        self.m_labelDuration = QLabel()
        self.m_labelDuration.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sliderLayout.addWidget(self.m_labelDuration, stretch=0)

        mainLayout.addLayout(sliderLayout)
        
        # Controls
        bottomRow.setContentsMargins(0, 0, 0, 0)

        self.controls = PlayerControls()
        self.controls.play.connect(self.m_player.play)
        self.controls.pause.connect(self.clickPause)
        self.controls.cut.connect(self.setCut)
        self.controls.cutPhase.connect(self.swapCutButton)
        self.controls.changeVolume.connect(self.m_audioOutput.setVolume)
        
        bottomRow.addWidget(self.controls)
        mainLayout.addLayout(bottomRow)

        # Key listeners
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, activated=self.clickPause)
        QShortcut(QKeySequence(Qt.Key.Key_C), self, activated=self.setCut)
        QShortcut(QKeySequence(Qt.Key.Key_S), self, activated=self.swapCutButton)

        QShortcut(QKeySequence(Qt.Key.Key_Left), self,
                  activated=lambda: self.nudge(-1000))   # −1s
        QShortcut(QKeySequence(Qt.Key.Key_Right), self,
                  activated=lambda: self.nudge(1000))    # +1s
        QShortcut(QKeySequence(Qt.SHIFT | Qt.Key.Key_Left), self,
                  activated=lambda: self.nudge(-100))    # −100ms
        QShortcut(QKeySequence(Qt.SHIFT | Qt.Key.Key_Right), self,
                  activated=lambda: self.nudge(100))     # +100ms

        ## Backwards implementation
        # self.m_player.playbackStateChanged.connect(controls.setState)
        # self.m_audioOutput.volumeChanged.connect(controls.setVolume)
        # self.m_audioOutput.mutedChanged.connect(controls.setMuted) # pushes controls to top

    @Slot()
    def nudge(self, delta_ms: int):
        self.m_player.setPosition(
            max(0, self.m_player.position() + delta_ms)
        )

    @Slot()
    def clickDelete(self):
        path = self.currentUrl.toLocalFile()
        print(f"Want to delete?: {getattr(self, "currentUrl")}")
        dialog = ConfirmDeleteDialog(self, filename=path)
        if dialog.exec():
        # user confirmed deletion
            self.m_player.stop()
            self.m_player.setSource(QUrl())
            os.remove(path)

    @Slot()
    def clickPause(self):
        if not getattr(self, "pause"):
            self.m_player.pause()
            self.pause = True
            return
        self.m_player.play()
        self.pause = False

    def setStart(self, ms):
        self.cut_startpos_ms = ms
        self.m_slider.setCutMarks(True, self.cut_startpos_ms)

    def setEnd(self, ms):
        self.cut_endpos_ms = ms
        self.m_slider.setCutMarks(False, self.cut_endpos_ms)

    @Slot()
    def swapCutButton(self):
        self.startBtnState = not self.startBtnState
        self.controls.swapCutText()

    @Slot()
    def setCut(self):
        ms = self.m_player.position()
        if self.cut_endpos_ms == 0:
            self.cut_endpos_ms = self.m_player.duration() - 100
        if self.startBtnState:
            self.setStart(ms)
        else:
            self.setEnd(ms)
        

    @Slot()
    def confirmCut(self):
        if not self.currentUrl:
            QMessageBox.warning(self, "No file", "Open a video file first.")
            return
    
        start_ms = self.cut_startpos_ms
        end_ms = self.cut_endpos_ms
        if end_ms <= start_ms:
            QMessageBox.warning(self, "Invalid cut", "End must be after Start.")
            return
    
        inp = self.currentUrl.toLocalFile()
        base_dir = os.path.dirname(inp)
        base_name = os.path.splitext(os.path.basename(inp))[0]
    
        default_out_name = f"CUT_{base_name}.mp4"
    
        dlg = ExportDialog(default_out_name, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
    
        out_name = dlg.filename()
        if not out_name:
            QMessageBox.warning(self, "Invalid name", "Please enter a filename.")
            return
    
        # ensure .mp4 extension
        if not out_name.lower().endswith(".mp4"):
            out_name += ".mp4"
    
        out_path = os.path.join(base_dir, out_name)
    
        start_s = start_ms / 1000.0
        end_s = end_ms / 1000.0
    
        try:
            self.cutToHighQuality(inp, out_path, start_s, end_s)
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Export failed", f"ffmpeg failed.\n\n{e}")
            return
    
        if dlg.delete_original():
            try:
                self.loadCutVideo = True
                self.cut_video_path = out_path
                self.open()
                os.remove(inp)
                QMessageBox.information(self, "Export complete", f"Original deleted, New file saved:\n{out_path}")
                return
            except OSError as e:
                QMessageBox.warning(self, "Export done (delete failed)",
                                    f"Clip exported to:\n{out_path}\n\nBut deleting the original failed:\n{e}")
                return
    
        QMessageBox.information(self, "Export complete", f"Saved:\n{out_path}")
        

    def cutToHighQuality(
        self,
        inp: str,
        out: str,
        start_s: float,
        end_s: float,
        crf: int = 20,
        preset: str = "veryfast",
        audio_kbps: int = 160,
    ):
        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()

        cmd = [
            ffmpeg_bin, "-y",
            "-i", inp,
            "-ss", f"{start_s:.3f}",
            "-to", f"{end_s:.3f}",
            "-map", "0:v:0?", "-map", "0:a:0?",
            "-c:v", "libx264",
            "-preset", preset,
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", f"{audio_kbps}k",
            out,
        ]

        print("FFMPEG COMMAND:")
        print(" ".join(cmd))

        subprocess.run(cmd, check=True)


    @Slot("qlonglong")
    def durationChanged(self, duration):
        self.m_duration = duration / 1000
        self.m_slider.setMaximum(duration)

    @Slot("qlonglong")
    def positionChanged(self, progress):
        if not self.m_slider.isSliderDown():
            self.m_slider.setValue(progress)
        self.updateDurationInfo(progress / 1000)

    def updateDurationInfo(self, currentInfo):
        tStr = ""
        if currentInfo or self.m_duration:
            currentTime = QTime((currentInfo / 3600) % 60, (currentInfo / 60) % 60,
                                currentInfo % 60, (currentInfo * 1000) % 1000)
            totalTime = QTime((self.m_duration / 3600) % 60, (self.m_duration / 60) % 60,
                              self.m_duration % 60, (self.m_duration * 1000) % 1000)
            format = "hh:mm:ss" if self.m_duration > 3600 else "mm:ss"
            tStr = currentTime.toString(format) + " / " + totalTime.toString(format)
        self.m_labelDuration.setText(tStr)

    @Slot(int)
    def seek(self, mseconds):
        self.m_player.setPosition(mseconds)

    @Slot()
    def displayErrorMessage(self):
        print("ERROR:", self.m_player.error(), self.m_player.errorString())

    def open(self):
        # File opening
        self.pause = False
        self.currentUrl = ""
        self.cut_startpos_ms = 0
        self.cut_endpos_ms = 0
        self.startBtnState = True
        self.m_slider.removeCutMarks()
        fileDialog = QFileDialog(self)
        fileDialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        fileDialog.setWindowTitle("Open Files")
        fileDialog.setNameFilters(["Videos (*.mkv *.mp4 *.mov)"])
        fileDialog.setDirectory(r"C:\Users\Anti\Desktop\streaming career\clips util\OBS output")
        if getattr(self, "loadCutVideo"):
            self.openUrl(QUrl.fromLocalFile(getattr(self, "cut_video_path")))
            self.loadCutVideo = False
            return
        if fileDialog.exec() == QDialog.DialogCode.Accepted:
            self.openUrl(fileDialog.selectedUrls()[0])

    def openUrl(self, url):
        self.currentUrl = url
        self.m_player.setSource(url)
        self.fileLabel.setText(str(self.currentUrl.toLocalFile()))
        self.m_player.play()

def convertToMinSeconds(ms: int)->str:
    duration = datetime.timedelta(milliseconds=ms)
    return "0: "+ str(duration.seconds)

if __name__ == "__main__":
    app = QApplication([])
    player = Player()
    player.resize(900, 600)
    player.show()
    app.exec()

 