import Aufblaspruefstand_GUI
from PyQt5 import QtWidgets, QtGui, QtCore, uic
from datetime import datetime
import numpy as np
import cv2
import serial
import pyqtgraph as pg

# src: https://gist.github.com/docPhil99/ca4da12c9d6f29b9cea137b617c7b8b1


class Worker_Video(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    signal_change_pixmap = QtCore.pyqtSignal(object)

    def __init__(self, h_min, h_max, s_min, s_max, v_min, v_max):
        super().__init__()
        self.run_flag = True
        self.h_min = h_min
        self.h_max = h_max
        self.s_min = s_min
        self.s_max = s_max
        self.v_min = v_min
        self.v_max = v_max


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
        
        while self.run_flag:
            ret, cv_img = cap.read()
            if ret:
                self.signal_change_pixmap.emit(cv_img)
        
        # Videosignal trennen
        cap.release()
        
        self.finished.emit()


    def Stop(self):
        self.run_flag = False


class Worker_Druck(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    signal_zeit_druck = QtCore.pyqtSignal(float, float)
    
    def __init__(self, time_start, port):
        super().__init__()
        self.run_flag = True
        self.time_start = time_start
        self.ser = serial.Serial(port, 9600)

        
        # Werte zur Konvertierung des seriellen Signals von Volt in mbar definieren
        self.v_in = 3.3                   # input voltage in V
        self.v_0  = self.v_in/10          # voltage at  0psi (10% of v_in)
        self.v_10 = self.v_in-self.v_0    # voltage at 10psi (90% of v_in)


    @QtCore.pyqtSlot()
    def Start(self):
        while self.run_flag:
            # Zeitdifferenz zur Startzeit berechnen
            dt = (datetime.now() - self.time_start).total_seconds()
        
            # read 16bit serial value, convert to string as UTF-8, rstrip newline-character and ...
            try:
                # convert to int
                sensorVal = int(str(self.ser.readline(), 'UTF-8').rstrip('\n'))
            except ValueError:
                # convert to float
                sensorVal = float(str(self.ser.readline(), 'UTF-8').rstrip('\n'))
            
            # convert 16bit integer to Volt
            voltage = sensorVal*self.v_in/(2**16)
            
            # convert Volt to psi (0.1*v_in == v_0 == 0psi ; 0.9*v_in == v_10 == 10psi)
            m = 10/(self.v_10-self.v_0)
            b = -self.v_0*m
            p_psi = m*voltage + b
    
            # convert psi to mbar
            p_mbar = 68.9476*p_psi
            
            self.signal_zeit_druck.emit(dt, p_mbar)
            
        self.finished.emit()
        self.ser.close()  # Verbindung zur seriellen Schnittstelle trennen


    def Stop(self):
        self.run_flag = False


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
        # Falls Datei nicht vorhanden ist, werden die Werte auf Standardwerte gesetzt
        except TypeError:
            self.Slider_zuruecksetzen()
        
        # Zusammenhaenge zwischen Knoepfen in der GUI (Frontend) und Funktionen dieses Skripts (Backend) definieren
        self.pushButtonReset.clicked.connect(self.Slider_zuruecksetzen)
        self.pushButtonMessungStarten.clicked.connect(self.Messung_starten)
        self.pushButtonMessungBeenden.clicked.connect(self.Messung_beenden)
        
        # Werte Video
        self.video_width = 640
        self.video_height = 480
        self.image_label.resize(self.video_width, self.video_height)
        self.thread_video = None
        
        # Werte Druckmessung
        self.port = 'COM6'  # serieller Port (Pi Pico)
        self.thread_druck = None
        
        # GraphicsLayoutWidget fuer Plot in der GUI
        label_styles = {'color':'r', 'font-size':'12pt'}
        self.plot_GraphicsLayoutWidget.setBackground('w')
        self.plotitem_p_over_t = self.plot_GraphicsLayoutWidget.addPlot(row=0, col=0)
        self.plotitem_d_over_t = self.plot_GraphicsLayoutWidget.addPlot(row=1, col=0)
        self.plotitem_p_over_d = self.plot_GraphicsLayoutWidget.addPlot(row=2, col=0)
        self.plotitem_d_over_t.setXLink(self.plotitem_p_over_t)
        self.plotitem_p_over_t.setMouseEnabled(x=False, y=False)
        self.plotitem_d_over_t.setMouseEnabled(x=False, y=False)
        self.plotitem_p_over_d.setMouseEnabled(x=False, y=False)
        self.plotitem_p_over_t.setLabel('left', 'Druck / mbar', **label_styles)
        self.plotitem_d_over_t.setLabel('left', 'Durchmesser / mm', **label_styles)
        self.plotitem_d_over_t.setLabel('bottom', 'Versuchslaufzeit / s', **label_styles)
        self.plotitem_p_over_d.setLabel('left', 'Druck / mbar', **label_styles)
        self.plotitem_p_over_d.setLabel('bottom', 'Durchmesser / mm', **label_styles)
        self.scatterplotitem_p_over_t = pg.ScatterPlotItem(size=10, brush=pg.mkBrush(0, 86, 148, 120))
        self.scatterplotitem_d_over_t = pg.ScatterPlotItem(size=10, brush=pg.mkBrush(0, 86, 148, 120))
        self.scatterplotitem_p_over_d = pg.ScatterPlotItem(size=10, brush=pg.mkBrush(0, 86, 148, 120))
        self.plotitem_p_over_t.addItem(self.scatterplotitem_p_over_t)
        self.plotitem_d_over_t.addItem(self.scatterplotitem_d_over_t)
        self.plotitem_p_over_d.addItem(self.scatterplotitem_p_over_d)
        self.plotdataitem_p_over_t = self.plotitem_p_over_t.plot()
        self.plotdataitem_d_over_t = self.plotitem_d_over_t.plot()
        self.plotdataitem_p_over_d = self.plotitem_p_over_d.plot()
        
        # Interaktion mit der GUI aktivieren
        self.interaktion_aktivieren()
        
        # Video starten
        self.Video_starten()
    
    
    def Messung_starten(self):
        # Startzeit merken
        self.time_start = datetime.now()
    
        # initialize lists for time, pressure and diameter
        self.time_pressure = []
        self.time_diameter = []
        self.pressure = []
        self.diameter = []
        
        # Worker und Thread initialisieren (jeweils ohne 'parent', Quelle: https://stackoverflow.com/a/33453124)
        self.worker_druck = Worker_Druck(self.time_start, self.port)
        self.thread_druck = QtCore.QThread()
        
        # Worker dem Thread hinzufuegen
        self.worker_druck.moveToThread(self.thread_druck)
        
        # Signale von Workern und Threads mit Slots (Funktionen) verknuepfen
        self.worker_druck.finished.connect(self.thread_druck.quit)   # Wenn Worker das Signal 'finished' sendet, wird der Thread beendet
        self.worker_druck.finished.connect(lambda: print('Worker finished'))
        self.worker_druck.signal_zeit_druck.connect(lambda z, d: self.update_plot_p_over_t(z, d))
        self.thread_druck.started.connect(self.worker_druck.Start)  # Wenn Thread gestartet wird, wird im Worker die Funktion 'Start' ausgefuehrt
        self.thread_druck.finished.connect(self.Thread_druck_deaktivieren)   # Wenn Thread beendet ist, wird die Funktion 'Thread_druck_deaktivieren' ausgefuehrt

        # Plotdaten der Auswertung leeren
        self.scatterplotitem_p_over_t.clear()
        self.scatterplotitem_d_over_t.clear()
        self.scatterplotitem_p_over_d.clear()

        # Interaktion mit der GUI deaktivieren
        self.interaktion_deaktivieren()

        # Thread starten
        self.thread_druck.start()


    def Messung_beenden(self):
        if self.thread_druck.isRunning():
            reply = QtWidgets.QMessageBox.question(self, 'Warnung', 'Die Messung ist noch aktiv. Soll diese beendet werden?',
                    QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.No:
                return

        self.worker_druck.Stop()
        
        # Interaktion mit der GUI aktivieren
        self.interaktion_aktivieren()

        print("Task wurde manuell beendet!")
        return


    def update_plot_p_over_t(self, dt, p_mbar):
        #print(dt, p_mbar)
        self.scatterplotitem_p_over_t.addPoints(x=[dt], y=[p_mbar])


    def Thread_druck_deaktivieren(self):
        self.thread_druck = None


    def Video_starten(self):
        # Worker und Thread initialisieren (jeweils ohne 'parent', Quelle: https://stackoverflow.com/a/33453124)
        self.worker_video = Worker_Video(self.hMinSlider.value(),
                                         self.hMaxSlider.value(),
                                         self.sMinSlider.value(),
                                         self.sMaxSlider.value(),
                                         self.vMinSlider.value(),
                                         self.vMaxSlider.value())
        self.thread_video = QtCore.QThread()
        
        # Worker dem Thread hinzufuegen
        self.worker_video.moveToThread(self.thread_video)
        
        # Signale von Workern und Threads mit Slots (Funktionen) verknuepfen
        self.worker_video.finished.connect(self.thread_video.quit)   # Wenn Worker das Signal 'finished' sendet, wird der Thread beendet
        self.worker_video.finished.connect(lambda: print('Worker finished'))
        self.worker_video.signal_change_pixmap.connect(lambda ci: self.update_image(ci))
        self.thread_video.started.connect(self.worker_video.Start)  # Wenn Thread gestartet wird, wird im Worker die Funktion 'Start' ausgefuehrt
        self.thread_video.finished.connect(self.Thread_video_deaktivieren)   # Wenn Thread beendet ist, wird die Funktion 'Thread_video_deaktivieren' ausgefuehrt
        
        # Thread starten
        self.thread_video.start()


    def update_image(self, cv_img):
        cv_img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)   # cv2.COLOR_BGR2HSV
        h, w, ch = cv_img_rgb.shape
        bytes_per_line = ch * w
        qt_img = QtGui.QImage(cv_img_rgb.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        #qt_img = qt_img.scaled(self.video_width, self.video_height, QtCore.Qt.KeepAspectRatio)
        self.image_label.setPixmap(QtGui.QPixmap.fromImage(qt_img))


    def Thread_video_deaktivieren(self):
        self.thread_video = None


    def interaktion_aktivieren(self):
        # Buttons (de)aktivieren
        self.pushButtonMessungStarten.setEnabled(True)
        self.pushButtonMessungBeenden.setEnabled(False)
        self.pushButtonReset.setEnabled(True)
        
        # Slider aktivieren
        self.hMinSlider.setEnabled(True)
        self.hMaxSlider.setEnabled(True)
        self.sMinSlider.setEnabled(True)
        self.sMaxSlider.setEnabled(True)
        self.vMinSlider.setEnabled(True)
        self.vMaxSlider.setEnabled(True)
        self.minAreaSlider.setEnabled(True)


    def interaktion_deaktivieren(self):
        # Buttons (de)aktivieren
        self.pushButtonMessungStarten.setEnabled(False)
        self.pushButtonMessungBeenden.setEnabled(True)
        self.pushButtonReset.setEnabled(False)
        
        # Slider deaktivieren
        self.hMinSlider.setEnabled(False)
        self.hMaxSlider.setEnabled(False)
        self.sMinSlider.setEnabled(False)
        self.sMaxSlider.setEnabled(False)
        self.vMinSlider.setEnabled(False)
        self.vMaxSlider.setEnabled(False)
        self.minAreaSlider.setEnabled(False)


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
        # Feststellen, ob ein Thread aktiv ist
        if self.thread_video is not None and self.thread_video.isRunning():
            self.worker_video.Stop()
            #self.thread_video.requestInterruption()    # Dieser Request muss im Worker explizit verarbeitet werden
        if self.thread_druck is not None and self.thread_druck.isRunning():
            self.thread_druck.requestInterruption()
        
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
