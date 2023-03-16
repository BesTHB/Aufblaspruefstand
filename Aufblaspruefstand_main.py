import Aufblaspruefstand_GUI
from PyQt5 import QtWidgets, QtGui, QtCore, uic
from datetime import datetime
import numpy as np
import cv2


class Worker_Video(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    signal_change_pixmap = QtCore.pyqtSignal(object)

    def __init__(self, time_start):
        super().__init__()


    @QtCore.pyqtSlot()
    def Start(self):
        """
        In dieser Funktion findet die Videoaufnahme statt.
        Der Aufruf dieser Funktion findet in der Funktion 'Video_starten' statt.
        """
        
        # Videosignal holen
        cap = cv2.VideoCapture(0)
        
        # set displayed size of the webcam image/video
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        while True:
            ret, cv_img = cap.read()
            if ret:
                self.signal_change_pixmap.emit(cv_img)
        
        # Videosignal trennen
        cap.release()
        
        self.finished.emit()


class DieseApp(QtWidgets.QMainWindow, Aufblaspruefstand_GUI.Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)  # Einfach gesagt: das erlaubt uns, Variablen aus der GUI-Datei aufzurufen

        self.setupUi(self)
        
        # Datei fuer Einstellungen des Nutzers definieren und Werte daraus laden
        self.settings = QtCore.QSettings('./values.ini', QtCore.QSettings.IniFormat)
        try:
            self.hMinSlider.setValue(self.settings.value('h_min'))
            self.hMaxSlider.setValue(self.settings.value('h_max'))
            self.sMinSlider.setValue(self.settings.value('s_min'))
            self.sMaxSlider.setValue(self.settings.value('s_max'))
            self.vMinSlider.setValue(self.settings.value('v_min'))
            self.vMaxSlider.setValue(self.settings.value('v_max'))
            self.minAreaSlider.setValue(self.settings.value('area_min'))
        # Falls Datei nicht vorhanden ist, werden die Werte auf Standardwerte gesetzt.
        except TypeError:
            self.Slider_zuruecksetzen()
        
        # Zusammenhaenge zwischen Knoepfen in der GUI (Frontend) und Funktionen dieses Skripts (Backend) definieren
        self.pushButtonReset.clicked.connect(self.Slider_zuruecksetzen)
        
        # Startzeit merken
        self.time_start = datetime.now()
        
        self.video_width = 640
        self.video_height = 480
        self.image_label.resize(self.video_width, self.video_height)
        
        # Video starten
        self.Video_starten()
        

    def Video_starten(self):
        # Worker und Thread initialisieren (jeweils ohne 'parent', Quelle: https://stackoverflow.com/a/33453124)
        self.worker_video = Worker_Video(self.time_start)
        self.thread_video = QtCore.QThread()
        
        # Thread dem Worker hinzufuegen
        self.worker_video.moveToThread(self.thread_video)
        
        # TODO: Signale von Worker und Thread mit Slots (Funktionen) verknuepfen
        self.worker_video.finished.connect(self.thread_video.quit)   # Wenn Worker das Signal 'finished' sendet, wird der Thread beendet
        self.worker_video.finished.connect(lambda: print('Worker finished'))
        self.worker_video.signal_change_pixmap.connect(lambda ci: self.update_image(ci))
        self.thread_video.started.connect(self.worker_video.Start)  # Wenn Thread gestartet wird, wird im Worker die Funktion 'Start' ausgefuehrt
        self.thread_video.finished.connect(self.Thread_video_deaktivieren)   # Wenn Thread beendet ist, wird die Funktion 'Thread_video_deaktivieren' ausgefuehrt
        
        # Thread starten
        self.thread_video.start()


    def update_image(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        qt_img = convert_to_qt_format.scaled(self.video_width, self.video_height, QtCore.Qt.KeepAspectRatio)
        self.image_label.setPixmap(QtGui.QPixmap.fromImage(qt_img))


    def Thread_video_deaktivieren(self):
        self.thread_video = None


    def Slider_zuruecksetzen(self):
        """
        Diese Funktion wird ausgefuehrt, wenn in der GUI der Reset-Button gedrueckt wird.
        """
        self.hMinSlider.setValue(60)
        self.hMaxSlider.setValue(88)
        self.sMinSlider.setValue(80)
        self.sMaxSlider.setValue(255)
        self.vMinSlider.setValue(90)
        self.vMaxSlider.setValue(255)
        self.minAreaSlider.setValue(60)
    
    
    def closeEvent(self, event):
        # Dieser Fall tritt ein, wenn kein Thread (mehr) vorliegt
        if self.thread_video is not None:
            self.thread_video.requestInterruption()    # Dieser Request muss im Worker explizit verarbeitet werden
        
        # TODO: AskYesNo, ob eingestellte Werte beim Beenden gespeichert werden sollen
        self.settings.setValue('h_min', self.hMinSlider.value())
        self.settings.setValue('h_max', self.hMaxSlider.value())
        self.settings.setValue('s_min', self.sMinSlider.value())
        self.settings.setValue('s_max', self.sMaxSlider.value())
        self.settings.setValue('v_min', self.vMinSlider.value())
        self.settings.setValue('v_max', self.vMaxSlider.value())
        self.settings.setValue('area_min', self.minAreaSlider.value())

        event.accept()


def main():
    app = QtWidgets.QApplication([])
    form = DieseApp()
    form.show()
    app.exec()


if __name__ == '__main__':
    main()
