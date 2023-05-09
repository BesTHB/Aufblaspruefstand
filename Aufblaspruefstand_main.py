import Aufblaspruefstand_GUI
import cv2
import logging
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyqtgraph as pg
import serial
from datetime import datetime
from pathlib import Path
from PyQt5 import QtWidgets, QtGui, QtCore, uic
from scipy import signal


# src: https://gist.github.com/docPhil99/ca4da12c9d6f29b9cea137b617c7b8b1

# TODO:
# - Code kommentieren


class Worker_Video(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    signal_change_pixmap = QtCore.pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.run_flag = True


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
    signal_zeit_druck = QtCore.pyqtSignal(object, float)

    def __init__(self, port):
        super().__init__()
        self.run_flag = True

        # Werte zur Konvertierung des seriellen Signals von Volt in mbar definieren
        self.v_in = 3.3                   # input voltage in V
        self.v_0  = self.v_in/10          # voltage at  0psi (10% of v_in)
        self.v_10 = self.v_in-self.v_0    # voltage at 10psi (90% of v_in)


    @QtCore.pyqtSlot()
    def Start(self):
        while self.run_flag:
            # read 16bit serial value, convert to string as UTF-8, rstrip newline-character and ...
            try:
                # convert to int
                sensorVal = int(str(ser.readline(), 'UTF-8').rstrip('\n'))
            except ValueError:
                # convert to float
                sensorVal = float(str(ser.readline(), 'UTF-8').rstrip('\n'))

            # Zeitpunkt der Messung festhalten
            t_druck = datetime.now()

            # convert 16bit integer to Volt
            voltage = sensorVal*self.v_in/(2**16)

            # convert Volt to psi (0.1*v_in == v_0 == 0psi ; 0.9*v_in == v_10 == 10psi)
            m = 10/(self.v_10-self.v_0)
            b = -self.v_0*m
            p_psi = m*voltage + b

            # convert psi to mbar
            p_mbar = 68.9476*p_psi

            self.signal_zeit_druck.emit(t_druck, p_mbar)

        self.finished.emit()

    def Stop(self):
        self.run_flag = False


class Logger_QTextEdit(logging.Handler, QtCore.QObject):
    signal_appendPlainText = QtCore.pyqtSignal(object)

    def __init__(self):
        logging.Handler.__init__(self)
        QtCore.QObject.__init__(self)

    def emit(self, log):
        msg = self.format(log)
        self.signal_appendPlainText.emit(msg)


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

        # Tauschordner (fuer Infomonitor setzen) --> //IP.IP.IP.IP/Infomonitor_Austausch/  (manuell in values.ini setzen!)
        try:
            self.tauschordner = self.settings.value('tauschordner')
        except:
            self.tauschordner = './'

        # Log-Handler fuer GUI-Fenster anlegen
        self.gui_loghandler = Logger_QTextEdit()
        self.gui_loghandler.signal_appendPlainText.connect(self.plainTextEdit_Log.appendPlainText)

        self.logger = logging.getLogger('./')  # Logger initialisieren (der Logger bekommt als eindeutigen Namen den Namen des Zielordners)
        self.logger.handlers = []              # bisherige Handler des Loggers loeschen

        # Log-Handler anlegen, Quelle: https://realpython.com/python-logging/#using-handlers
        log_handler_stream = logging.StreamHandler()

        self.logger.setLevel(logging.INFO)

        # Log-Format definieren und den Handlern zuweisen
        self.log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%d.%m.%y, %H:%M:%S')
        log_handler_stream.setFormatter(self.log_format)
        self.gui_loghandler.setFormatter(self.log_format)

        # Handler dem Logger hinzufuegen
        self.logger.addHandler(log_handler_stream)
        self.logger.addHandler(self.gui_loghandler)

        # Zusammenhaenge zwischen Knoepfen (etc.) in der GUI (Frontend) und Funktionen dieses Skripts (Backend) definieren
        self.pushButtonReset.clicked.connect(self.Slider_zuruecksetzen)
        self.pushButtonMessungStarten.clicked.connect(self.Messung_starten)
        self.pushButtonMessungBeenden.clicked.connect(self.Messung_beenden)
        self.pushButtonBildWechseln.clicked.connect(self.Bild_wechseln)
        self.pushButtonScreenshot.clicked.connect(self.Screenshot_speichern)

        # Werte Video
        self.video_width = 640
        self.video_height = 480
        self.image_label.resize(self.video_width, self.video_height)
        self.thread_video = None
        self.time_last_diameter_query = datetime.now()
        self.save_img = False  # Flag, ob Screenshot gespeichert werden soll

        # Liste fuer Bilder und Index des anzuzeigenden Bildes (original, gefiltert) initialisieren
        self.imgs = [None, None]
        self.img_index = 0

        # setup aruco marker
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

        # Werte Druckmessung
        self.port = 'COM6'  # serieller Port (Pi Pico)
        self.thread_druck = None
        self.dt_serial = 0.2  # Zeitdifferenz zwischen zwei Eingaengen des Druckmesssignals der seriellen Schnittstelle

        # GraphicsLayoutWidget fuer Plot in der GUI
        label_styles = {'color':'r', 'font-size':'12pt'}
        self.plot_GraphicsLayoutWidget.setBackground('w')
        self.plotitem_p_over_t = self.plot_GraphicsLayoutWidget.addPlot(row=0, col=0)
        self.plotitem_d_over_t = self.plot_GraphicsLayoutWidget.addPlot(row=1, col=0)
        self.plotitem_d_over_t.setXLink(self.plotitem_p_over_t)
        self.plotitem_p_over_t.setMouseEnabled(x=False, y=False)
        self.plotitem_d_over_t.setMouseEnabled(x=False, y=False)
        self.plotitem_p_over_t.setLabel('left', 'Druck / mbar', **label_styles)
        self.plotitem_d_over_t.setLabel('left', 'Durchmesser / mm', **label_styles)
        self.plotitem_d_over_t.setLabel('bottom', 'Versuchslaufzeit / s', **label_styles)
        self.scatterplotitem_p_over_t = pg.ScatterPlotItem(size=10, brush=pg.mkBrush(0, 86, 148, 120))
        self.scatterplotitem_d_over_t = pg.ScatterPlotItem(size=10, brush=pg.mkBrush(0, 86, 148, 120))
        self.plotitem_p_over_t.addItem(self.scatterplotitem_p_over_t)
        self.plotitem_d_over_t.addItem(self.scatterplotitem_d_over_t)
        self.plotdataitem_p_over_t = self.plotitem_p_over_t.plot()
        self.plotdataitem_d_over_t = self.plotitem_d_over_t.plot()

        # Interaktion mit der GUI aktivieren
        self.interaktion_aktivieren()

        # Video starten
        self.Video_starten()


    def Messung_starten(self):
        # Durchmesser aus GUI-Eingabe extrahieren, bis zu denen je Zyklus aufgeblasen werden soll.
        try:
            self.zyklen_durchmesser = [float(x) for x in self.lineEdit_Durchmesser_Zyklen.text().strip().replace(' ','').split(',')]
        except ValueError:
            self.logger.warning('Bitte kontrollieren Sie die Eingabe der Durchmesser je Zyklus. Die Messung wurde nicht gestartet.')
            return

        # Testen, ob alle Werte den Mindestwert erfuellen
        d_min = 60
        if any([x < d_min for x in self.zyklen_durchmesser]):
            self.logger.warning(f'Der Mindestdurchmesser ist {d_min}mm. Die Messung wurde nicht gestartet.')
            return

        # Testen, ob alle Werte den Maximalwert erfuellen
        d_max = 210
        if any([x > d_max for x in self.zyklen_durchmesser]):
            self.logger.warning(f'Der Maximaldurchmesser ist {d_max}mm. Die Messung wurde nicht gestartet.')
            return

        # Startzeit merken
        self.time_start = datetime.now()

        # Output-Ordner anlegen
        self.outdir = f'./Messungen/{self.time_start.strftime("%Y_%m_%d__%H_%M_%S")}/'   # mit '/' am Ende!
        Path(self.outdir).mkdir(parents=True)

        # Log-Handler fuer Logging in Datei hinzufuegen
        self.log_handler_file = logging.FileHandler(self.outdir+'Log.txt')
        self.log_handler_file.setFormatter(self.log_format)
        self.logger.addHandler(self.log_handler_file)

        self.logger.info('Messung gestartet mit folgenden Einstellungen:')
        self.logger.info(f'H = [{self.hMinSlider.value()}, {self.hMaxSlider.value()}]')
        self.logger.info(f'S = [{self.sMinSlider.value()}, {self.sMaxSlider.value()}]')
        self.logger.info(f'V = [{self.vMinSlider.value()}, {self.vMaxSlider.value()}]')
        self.logger.info(f'min. Area = {self.minAreaSlider.value()}')

        # Durchmesserwerte loggen
        tmp_str = ''
        for d in self.zyklen_durchmesser:
            tmp_str += f'{d}, '
        tmp_str = tmp_str.rstrip(', ')
        self.logger.info(f'Durchmesserzyklen: [{tmp_str}]')

        # Werte fuer automatisches Oeffnen/Schliessen des Magnetventils initialisieren
        self.aufblasen = True
        self.entlueften_beendet = False
        self.zyklus = 0
        self.zeit_ende_entlueften = datetime.now()
        self.verzoegerung_aufblasen = 2  # Sekunden
        self.diameter_written = False

        # serielle Schnittstelle verbinden und Magnetventil oeffnen
        global ser
        ser = serial.Serial(self.port, 9600)
        ser.write(b'o')

        # initialize lists for time, pressure, diameter and cycle
        self.time_pressure = []
        self.time_diameter = []
        self.pressure = []
        self.diameter = []
        self.cycle = []

        # Worker und Thread initialisieren (jeweils ohne 'parent', Quelle: https://stackoverflow.com/a/33453124)
        self.worker_druck = Worker_Druck(self.port)
        self.thread_druck = QtCore.QThread()

        # Worker dem Thread hinzufuegen
        self.worker_druck.moveToThread(self.thread_druck)

        # Signale von Workern und Threads mit Slots (Funktionen) verknuepfen
        self.worker_druck.finished.connect(self.thread_druck.quit)   # Wenn Worker das Signal 'finished' sendet, wird der Thread beendet
        self.worker_druck.finished.connect(lambda: self.logger.info('Worker finished'))
        self.worker_druck.signal_zeit_druck.connect(lambda t_druck, p_mbar: self.update_lists_and_plot_p_over_t(t_druck, p_mbar))
        self.thread_druck.started.connect(self.worker_druck.Start)  # Wenn Thread gestartet wird, wird im Worker die Funktion 'Start' ausgefuehrt
        self.thread_druck.finished.connect(self.Thread_druck_deaktivieren)   # Wenn Thread beendet ist, wird die Funktion 'Thread_druck_deaktivieren' ausgefuehrt

        # Plotdaten der Auswertung leeren
        self.scatterplotitem_p_over_t.clear()
        self.scatterplotitem_d_over_t.clear()

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

        # Pandas DataFrames anlegen und speichern
        outfile_druck = self.outdir + 'Druck.txt'
        self.df_druck = pd.DataFrame({'Zeitpunkt Messung': self.time_pressure, 'Druck / mbar': self.pressure})
        self.df_druck.to_csv(outfile_druck, sep=';', encoding='utf-8', index=False, header=True)
        self.logger.info(f'Speichere aufgezeichnete Druckmessung in {outfile_druck} ab.')

        outfile_durchmesser = self.outdir + 'Durchmesser.txt'
        self.df_durchmesser = pd.DataFrame({'Zeitpunkt Messung': self.time_diameter, 'Durchmesser / mm': self.diameter, 'Zyklus': self.cycle})
        self.df_durchmesser.to_csv(outfile_durchmesser, sep=';', encoding='utf-8', index=False, header=True)
        self.logger.info(f'Speichere aufgezeichnete Durchmessermessung in {outfile_durchmesser} ab.')

        # Messung auswerten
        self.Messung_auswerten()

        # Interaktion mit der GUI aktivieren
        self.interaktion_aktivieren()

        self.logger.info("Task wurde manuell beendet!")
        self.logger.removeHandler(self.log_handler_file)

        # serielle Schnittstelle schliessen
        ser.write(b'c')  # sicherheitshalber das Magnetventil (ggf. nochmals) schliessen
        ser.close()
        return


    def Messung_auswerten(self):
        # Hier werden die Messungen zeitlich verknuepft, und zwar immer die zeitlich nahe liegendsten Druck- und Durchmessermessungen.
        # Es werden die Zeitstempel des erst genannten DataFrames beibehalten (hier: self.df_druck).
        df_merged = pd.merge_asof(self.df_druck, self.df_durchmesser, on='Zeitpunkt Messung', direction='nearest')

        # Von allen Zeitstempeln wird der erste Zeitstempel abgezogen, um die Versuchslaufzeit zu berechnen.
        # Anschliessend wird die Versuchslaufzeit in Sekunden umgewandelt.
        versuchslaufzeit = df_merged['Zeitpunkt Messung'] - df_merged['Zeitpunkt Messung'][0]
        df_merged['Versuchslaufzeit / s'] = versuchslaufzeit.dt.total_seconds()

        zeit = df_merged['Versuchslaufzeit / s'].to_numpy()
        druck = df_merged['Druck / mbar'].to_numpy()
        durchmesser = df_merged['Durchmesser / mm'].to_numpy()

        # Butterworth-Filter anwenden, um Druck- und Durchmessermessung zu glaetten
        bw_ord = 3
        bw_fc = 0.15
        b, a = signal.butter(bw_ord, bw_fc, 'low', analog=False, fs=5)
        w, h = signal.freqs(b, a)
        druck_gefiltert = signal.filtfilt(b, a, druck)
        durchmesser_gefiltert = signal.filtfilt(b, a, durchmesser)

        # Geglaettete Verlaeufe dem DataFrame hinzufuegen und herausschreiben
        df_merged['Druck (geglaettet) / mbar'] = druck_gefiltert
        df_merged['Durchmesser (geglaettet) / mm'] = durchmesser_gefiltert
        outfile_auswertung_txt = self.outdir + 'Auswertung.txt'
        df_merged.to_csv(outfile_auswertung_txt, sep=';', encoding='utf-8', index=False, header=True)
        self.logger.info(f'Speichere Daten der Auswertung in {outfile_auswertung_txt} ab.')

        blue = '#1f77b4'
        orange = '#ff7f0e'

        fig, axs = plt.subplots(3, 1)
        fig.tight_layout(pad=1.5)
        axs[0].plot(zeit, druck, c=blue)
        axs[0].plot(zeit, druck_gefiltert, c=orange)
        axs[0].set_ylabel('Druck / mbar')
        axs[0].locator_params(axis='y', nbins=5)

        axs[1].plot(zeit, durchmesser, c=blue)
        axs[1].plot(zeit, durchmesser_gefiltert, c=orange)
        axs[1].set_xlabel('Versuchslaufzeit / s')
        axs[1].set_ylabel('Durchmesser / mm')
        axs[1].locator_params(axis='y', nbins=5)

        #axs[2].plot(durchmesser, druck)
        axs[2].plot(durchmesser_gefiltert, druck_gefiltert, c=orange)
        axs[2].set_xlabel('Durchmesser / mm')
        axs[2].set_ylabel('Druck / mbar')
        axs[2].locator_params(axis='y', nbins=5)

        outfile_auswertung_pdf = self.outdir + 'Auswertung.pdf'
        plt.savefig(outfile_auswertung_pdf, format='pdf', bbox_inches='tight')
        self.logger.info(f'Speichere Plot mit Auswertung in {outfile_auswertung_pdf} ab.')

        try:
            outfile_infomonitor = self.tauschordner + 'Auswertung.pdf'
            plt.savefig(outfile_infomonitor, format='pdf', bbox_inches='tight')
            self.logger.info(f'Speichere Plot mit Auswertung in {outfile_infomonitor} ab.')
        except Exception as e:
            self.logger.error('Plot der Auswertung (fuer Infomonitor) konnte nicht gespeichert werden:\n{e}')


    def Screenshot_speichern(self):
        # Flag, ob Screenshot des naechsten Webcam-Bildes gespeichert werden soll
        self.save_img = True


    def update_lists_and_plot_p_over_t(self, t_druck, p_mbar):
        # Plot aktualisieren
        dt = (t_druck - self.time_start).total_seconds()
        self.scatterplotitem_p_over_t.addPoints(x=[dt], y=[p_mbar])

        # Werte zum spaeteren Herausschreiben sichern
        self.time_pressure.append(t_druck)
        self.pressure.append(p_mbar)


    def update_plot_d_over_t(self, dt, d):
        self.scatterplotitem_d_over_t.addPoints(x=[dt], y=[d])


    def Thread_druck_deaktivieren(self):
        self.thread_druck = None


    def Bild_wechseln(self):
        if self.img_index == 0:
            self.img_index = 1
        elif self.img_index == 1:
            self.img_index = 0


    def Video_starten(self):
        # Worker und Thread initialisieren (jeweils ohne 'parent', Quelle: https://stackoverflow.com/a/33453124)
        self.worker_video = Worker_Video()
        self.thread_video = QtCore.QThread()

        # Worker dem Thread hinzufuegen
        self.worker_video.moveToThread(self.thread_video)

        # Signale von Workern und Threads mit Slots (Funktionen) verknuepfen
        self.worker_video.finished.connect(self.thread_video.quit)   # Wenn Worker das Signal 'finished' sendet, wird der Thread beendet
        self.worker_video.finished.connect(lambda: self.logger.info('Worker finished'))
        self.worker_video.signal_change_pixmap.connect(lambda cv_img: self.update_image(cv_img))
        self.thread_video.started.connect(self.worker_video.Start)  # Wenn Thread gestartet wird, wird im Worker die Funktion 'Start' ausgefuehrt
        self.thread_video.started.connect(lambda: self.logger.info('Video gestartet.'))
        self.thread_video.finished.connect(self.Thread_video_deaktivieren)   # Wenn Thread beendet ist, wird die Funktion 'Thread_video_deaktivieren' ausgefuehrt

        # Thread starten
        self.thread_video.start()


    def update_image(self, cv_img):
        self.imgs[0] = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        cv_img_hsv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)

        hsv_min = np.array([self.hMinSlider.value(), self.sMinSlider.value(), self.vMinSlider.value()])
        hsv_max = np.array([self.hMaxSlider.value(), self.sMaxSlider.value(), self.vMaxSlider.value()])

        color_mask = cv2.inRange(cv_img_hsv, hsv_min, hsv_max)
        self.imgs[1] = cv2.bitwise_and(self.imgs[0], self.imgs[0], mask=color_mask)

        # detect aruco markers in current webcam image
        corners, ids, _ = cv2.aruco.detectMarkers(self.imgs[0], self.aruco_dict, parameters=self.aruco_params)

        # draw polygon around aruco markers
        int_corners = np.intp(corners)
        cv2.polylines(self.imgs[self.img_index], int_corners, True, (0, 255, 0), 2)

        try:
            # calculate the length of the polygon around the first detected aruco marker
            aruco_perimeter = cv2.arcLength(corners[0], True)  # in pixels

            # translate pixels to mm
            # (since the aruco marker is a square of side length 50mm, the length of the surrounding polygon must be 200mm)
            pixel_mm_ratio = aruco_perimeter / 200

            # calculate center of polygon and widths of aruco marker and display a text
            x, y = corners[0][0].mean(axis=0)
            s1, s2 = self.calc_aruco_widths(corners[0][0])
            cv2.putText(self.imgs[self.img_index], f'ID: {ids[0][0]}', (int(x), int(y)), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 0), 1)
            cv2.putText(self.imgs[self.img_index], f'[pixel] {s1:.2f} x {s2:.2f}', (int(x), int(y)-30), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 0), 1)
            cv2.putText(self.imgs[self.img_index], f'[mm] {s1/pixel_mm_ratio:.2f} x {s2/pixel_mm_ratio:.2f}', (int(x), int(y)-15), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 0), 1)

        # if currently no aruco marker is detected in the webcam image, corners[0] will throw an IndexError
        except IndexError:
            # Warnung anzeigen, dass aktuell kein Aruco-Marker detektiert wurde
            cv2.putText(self.imgs[self.img_index], 'Kein Aruco-Marker gefunden!', (int(self.video_width/10), int(self.video_height/2)), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 3)

        # detect contours, conversion to grayscale is necessary for findContours
        img_gray = cv2.cvtColor(self.imgs[1], cv2.COLOR_BGR2GRAY)
        contours, _ = cv2.findContours(img_gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for c in contours:
            area = cv2.contourArea(c)
            if area >= self.minAreaSlider.value():
                rect = cv2.minAreaRect(c)
                (x, y), (w, h), angle = rect
                box = cv2.boxPoints(rect)
                box = np.intp(box)
                cv2.polylines(self.imgs[self.img_index], [box], True, (255, 0, 0), 2)
                cv2.putText(self.imgs[self.img_index], f'[pixel] width: {w:.1f}, height: {h:.1f}', (int(x), int(y)+15), cv2.FONT_HERSHEY_PLAIN, 1, (255, 0, 0), 1)
                try:
                    durchmesser = w/pixel_mm_ratio
                    cv2.putText(self.imgs[self.img_index], f'[mm] width: {durchmesser:.2f}, height: {h/pixel_mm_ratio:.2f}', (int(x), int(y)+30), cv2.FONT_HERSHEY_PLAIN, 1, (255, 0, 0), 1)

                    # Vorsicht: Das Originalbild sollte mit HSV so eingestellt sein, dass nur EINE Box (naemlich um den Luftballon) gezeichnet wird.
                    # Sonst werden naemlich die Weiten mehrerer Objekte geplottet!
                    if self.messung_aktiv:

                        # Der Durchmesser soll im gleichen Takt gemessen werden, wie der Druck, also alle self.dt_serial Sekunden
                        now = datetime.now()
                        if (now-self.time_last_diameter_query).total_seconds() >= self.dt_serial:
                            # Plot aktualisieren
                            dt = (now - self.time_start).total_seconds()
                            self.update_plot_d_over_t(dt, durchmesser)

                            # Werte zum spaeteren Herausschreiben sichern
                            self.time_diameter.append(now)
                            self.diameter.append(durchmesser)

                            self.time_last_diameter_query = datetime.now()

                            # Flag speichern, ob akt. Durchmesser herausgeschrieben wurde,
                            # um weiter unten auch den Zyklus herausschreiben zu koennen
                            self.diameter_written = True
                        else:
                            self.diameter_written = False

                        # Feststellen, ob Magnetventil geoeffnet/geschlossen werden soll
                        # Falls Durchmesser beim Aufblasen 4x hintereinander ueber den Solldurchmesser des akt. Zyklus anwaechst, Magnetventil schliessen --> entlueften
                        if (self.aufblasen and all([x >= self.zyklen_durchmesser[self.zyklus] for x in self.diameter[-4:]])):
                            ser.write(b'c')
                            self.aufblasen = False
                            self.entlueften_beendet = False
                        # Falls Druck beim Entlueften unter 10 mbar faellt, Magnetventil oeffnen --> aufblasen
                        elif (not(self.aufblasen) and (self.pressure[-1] < 10)):
                            # Den Zeitpunkt des erstmaligen Betretens der Bedingung (<10 mbar) festhalten
                            if (not self.entlueften_beendet):
                                self.zeit_ende_entlueften = now
                                self.entlueften_beendet = True

                            # Erst nach der Verzoegerungszeit wieder erneut aufblasen,
                            # aber nur, falls die geforderten Zyklen noch nicht alle durchlaufen wurden
                            if (((now-self.zeit_ende_entlueften).total_seconds() >= self.verzoegerung_aufblasen) and (self.zyklus < len(self.zyklen_durchmesser)-1)):
                                ser.write(b'o')
                                self.aufblasen = True
                                self.zyklus += 1

                        # Falls der Durchmesser herausgeschrieben wurde, auch den akt. Zyklus herausschreiben
                        if self.diameter_written:
                            # Falls Aufblas- bzw. Entlueftungszyklus aktiv, speichere Zykluszahl,
                            # ansonsten schreibe -1 --> hilfreich fuer spaetere Auswertung
                            # Falls Aufblaszyklus aktiv
                            if self.aufblasen:
                                self.cycle.append(self.zyklus)
                            else:
                                # Falls Entlueftungszyklus aktiv, aber noch nicht beendet
                                if (self.aufblasen == self.entlueften_beendet):
                                    self.cycle.append(self.zyklus)
                                else:
                                    self.cycle.append(-1)

                except UnboundLocalError:
                    # if pixel_mm_ratio is not present, pass
                    pass

        # Das Bild in ein QImage konvertieren
        h, w, ch = self.imgs[self.img_index].shape
        bytes_per_line = ch * w
        qt_img = QtGui.QImage(self.imgs[self.img_index].data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        #qt_img = qt_img.scaled(self.video_width, self.video_height, QtCore.Qt.KeepAspectRatio)
        self.image_label.setPixmap(QtGui.QPixmap.fromImage(qt_img))

        # Das Bild abspeichern
        if self.save_img:
            # Output-Ordner fuer Screenshots anlegen, falls noch nicht vorhanden
            Path('./Screenshots/').mkdir(exist_ok=True)

            outfile_img = f'./Screenshots/Screenshot_{datetime.now().strftime("%Y_%m_%d__%H_%M_%S")}.png'
            cv2.imwrite(outfile_img, cv2.cvtColor(self.imgs[self.img_index], cv2.COLOR_RGB2BGR))  # Anmerkung: Bild muss als BGR (nicht RGB) vorliegen
            self.logger.info(f'Speichere Screenshot unter {outfile_img} ab.')

            # Flag zuruecksetzen
            self.save_img = False


    def calc_aruco_widths(self, c):
        x0, y0 = c[0]
        x1, y1 = c[1]
        x2, y2 = c[2]
        x3, y3 = c[3]
        wx = 0.5*np.sqrt( (x0+x3-x1-x2)**2 + (y0+y3-y1-y2)**2 )
        wy = 0.5*np.sqrt( (x0+x1-x2-x3)**2 + (y0+y1-y2-y3)**2 )
        return wx, wy


    def Thread_video_deaktivieren(self):
        self.thread_video = None


    def interaktion_aktivieren(self):
        # Buttons (de)aktivieren
        self.pushButtonMessungStarten.setEnabled(True)
        self.pushButtonMessungBeenden.setEnabled(False)
        self.pushButtonReset.setEnabled(True)
        self.pushButtonBildWechseln.setEnabled(True)

        # Slider aktivieren
        self.hMinSlider.setEnabled(True)
        self.hMaxSlider.setEnabled(True)
        self.sMinSlider.setEnabled(True)
        self.sMaxSlider.setEnabled(True)
        self.vMinSlider.setEnabled(True)
        self.vMaxSlider.setEnabled(True)
        self.minAreaSlider.setEnabled(True)

        # Flag, ob Messung aktiv
        self.messung_aktiv = False


    def interaktion_deaktivieren(self):
        # Buttons (de)aktivieren
        self.pushButtonMessungStarten.setEnabled(False)
        self.pushButtonMessungBeenden.setEnabled(True)
        self.pushButtonReset.setEnabled(False)
        self.pushButtonBildWechseln.setEnabled(False)

        # Slider deaktivieren
        self.hMinSlider.setEnabled(False)
        self.hMaxSlider.setEnabled(False)
        self.sMinSlider.setEnabled(False)
        self.sMaxSlider.setEnabled(False)
        self.vMinSlider.setEnabled(False)
        self.vMaxSlider.setEnabled(False)
        self.minAreaSlider.setEnabled(False)

        # Flag, ob Messung aktiv
        self.messung_aktiv = True


    def Slider_zuruecksetzen(self):
        """
        Diese Funktion wird ausgefuehrt, wenn in der GUI der Reset-Button gedrueckt wird.
        """
        self.hMinSlider.setValue(54)
        self.hMaxSlider.setValue(88)
        self.sMinSlider.setValue(81)
        self.sMaxSlider.setValue(255)
        self.vMinSlider.setValue(61)
        self.vMaxSlider.setValue(255)
        self.minAreaSlider.setValue(2400)


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
