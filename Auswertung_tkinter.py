import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
import matplotlib.pyplot as plt
import pandas as pd
import tkinter as tk
from scipy import signal


class Application:
    def __init__(self):
        # setup tkinter
        self.win = tk.Tk()
        self.win.title('Auswertung')
        self.win.geometry('1700x1200')
        self.win.protocol('WM_DELETE_WINDOW', self.destructor)

        # Read data
        self.infile = tk.filedialog.askopenfilename(title='Auswertung.txt öffnen', initialdir='./')
        df = pd.read_csv(self.infile, sep=';', decimal='.', header=0)

        # Save data in separate lists
        self.time_orig = df['Versuchslaufzeit / s'].to_list()
        self.pressure_orig = df['Druck / mbar'].to_list()
        self.diameter_orig = df['Durchmesser / mm'].to_list()

        # Kopien der Daten anlegen, in denen die Ausreisser entfernt werden sollen.
        # .copy() ist notwendig, da sonst die Originallisten bearbeitet werden
        self.time = self.time_orig.copy()
        self.pressure_raw = self.pressure_orig.copy()
        self.diameter_raw = self.diameter_orig.copy()

        # Daten zu Durchmesser-Ausreissern entfernen
        self.ausreisser_entfernen()

        # Define axis labels
        self.pressure_label = 'Pressure / mbar'
        self.diameter_label = 'Diameter / mm'
        self.time_label = 'Time / s'

        # Define colors for plot
        self.colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red']

        # initialize plot canvas
        self.fig, self.axs = plt.subplots(3, 1)
        self.fig.tight_layout(pad=1.5)
        self.plot_canvas = FigureCanvasTkAgg(self.fig, master=self.win)  # A tk.DrawingArea
        self.plot_canvas.draw()
        self.plot_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Indices of cycle starts with different load amplitudes -> different coloring
        self.start_cycles = [0, len(self.time)]  # min. [0, len(self.time)]

        # create sliders for butterworth filter
        self.bw_ord_init = 3
        self.bw_fc_init = 0.12  # < sampling_freq/2 (!)
        self.sampling_freq = 5  # Hz
        self.bw_ord = tk.IntVar()
        self.bw_fc = tk.DoubleVar()
        self.slider_bw_ord = tk.Scale(self.win, label='bw_ord', orient='horizontal', from_=1, to=6, resolution=1, variable=self.bw_ord, command=lambda x: self.update_plot())
        self.slider_bw_fc = tk.Scale(self.win, label='bw_fc', orient='horizontal', from_=0.02, to=self.sampling_freq/2-0.02, resolution=0.02, variable=self.bw_fc, command=lambda x: self.update_plot())
        self.slider_bw_ord.set(self.bw_ord_init)
        self.slider_bw_fc.set(self.bw_fc_init)
        self.slider_bw_ord.pack()
        self.slider_bw_fc.pack()

        # create buttons
        self.btn_reset = tk.Button(self.win, text='Reset', command=self.reset_values)
        self.btn_reset.pack()
        self.btn_save_plot = tk.Button(self.win, text='Save plot and data', command=self.save_plot_and_data)
        self.btn_save_plot.pack()

        # update plot
        self.update_plot()


    def update_plot(self):
        # apply lowpass digital Butterworth filter to raw measurements of pressure and diameter
        b, a = signal.butter(self.slider_bw_ord.get(), self.slider_bw_fc.get(), 'low', analog=False, fs=self.sampling_freq)
        w, h = signal.freqs(b, a)
        self.pressure_filtered = signal.filtfilt(b, a, self.pressure_raw)
        self.diameter_filtered = signal.filtfilt(b, a, self.diameter_raw)

        # clear plot
        self.axs[0].clear()
        self.axs[1].clear()
        self.axs[2].clear()

        # new plot
        # orig measurements
        self.axs[0].plot(self.time_orig, self.pressure_orig, c=self.colors[0], alpha=0.2)
        self.axs[1].plot(self.time_orig, self.diameter_orig, c=self.colors[0], alpha=0.2)
        # raw measurements
        self.axs[0].plot(self.time, self.pressure_raw, c=self.colors[0])
        self.axs[1].plot(self.time, self.diameter_raw, c=self.colors[0])

        # filtered/smoothed data, colored per load amplitude
        for i in range(len(self.start_cycles)-1):
            self.axs[0].plot(self.time[self.start_cycles[i]:self.start_cycles[i+1]], self.pressure_filtered[self.start_cycles[i]:self.start_cycles[i+1]], c=self.colors[i+1])
            self.axs[1].plot(self.time[self.start_cycles[i]:self.start_cycles[i+1]], self.diameter_filtered[self.start_cycles[i]:self.start_cycles[i+1]], c=self.colors[i+1])
            self.axs[2].plot(self.diameter_filtered[self.start_cycles[i]:self.start_cycles[i+1]], self.pressure_filtered[self.start_cycles[i]:self.start_cycles[i+1]], c=self.colors[i+1])

        self.axs[0].set_ylabel(self.pressure_label)
        self.axs[1].set_xlabel(self.time_label)
        self.axs[1].set_ylabel(self.diameter_label)
        self.axs[2].set_xlabel(self.diameter_label)
        self.axs[2].set_ylabel(self.pressure_label)
        self.axs[0].locator_params(axis='y', nbins=5)  # create 5 ticks on y-axis
        self.axs[1].locator_params(axis='y', nbins=5)
        self.axs[2].locator_params(axis='y', nbins=5)

        # update plot
        plt.draw()


    def ausreisser_entfernen(self):
        """
        Es tauchen in den Durchmesserwerten ggf. Ausreisser auf, die hier entfernt werden.
        Die Werte reissen (bislang) immer nur bis oben aus. Nur dies ist hier aktuell implementiert!
        In den Daten tauchten bislang maximal zwei Ausreisser hintereinander auf.
        Der Code sollte allerdings auch bei mehreren aufeinanderfolgenden Ausreissern funktionieren.
        """
        ausreisser_indices = []

        # Liste mit Durchmessern vom zweiten bis zum vorletzten Eintrag durchlaufen
        # und dabei immer einen Wert "nach links" und einen Wert "nach rechts" anschauen.
        for i in range(1, len(self.diameter_raw)-1):

            ind_mid   = i
            ind_right = i+1

            # Falls aktueller Index in Liste mit zu loeschenden Indizes ist (Ausreisser),
            # nach dem naechsten Index nach links suchen, der kein Ausreisser ist
            while ind_mid in ausreisser_indices:
                ind_mid -= 1

            # Falls linker Index in Liste mit zu loeschenden Indizes ist (Ausreisser),
            # nach dem naechsten Index nach links suchen, der kein Ausreisser ist
            ind_left = ind_mid-1
            while ind_left in ausreisser_indices:
                ind_left -= 1

            # Feststellen, ob der rechte Index mehr als 3% groesser als der Mittelwert des
            # linken und mittleren (aktuellen) Wertes ist
            if (-1 + self.diameter_raw[ind_right]/np.mean([self.diameter_raw[ind_left], self.diameter_raw[ind_mid]]) > 0.03):
                # Nur als Ausreisser markieren, falls Durchmesser ueber Schwellwert liegt.
                # (dies soll False-Positives -hauptsaechlich zu Beginn der Messung- beheben)
                # (ein niedriger Schwellwert sollte unkritisch sein, da Ausreisser aufgrund der staerkeren Reflektionen erst bei groesseren Durchmesser auftauchen)
                if self.diameter_raw[ind_mid] >= 70:
                    ausreisser_indices.append(ind_right)

        # Ausreisser in absteigender Reihenfolge aus der Liste loeschen,
        # da sonst die Indizes verschoben und falsche Werte geloescht werden wuerden
        print('Die folgenden Indizes (Werte in der Mitte) wurden als Ausreisser detektiert und geloescht:')
        for i in reversed(ausreisser_indices):
            del self.diameter_raw[i]
            del self.pressure_raw[i]
            del self.time[i]

            try:
                print(f'Index {i-1},{i},{i+1}: {self.diameter_orig[i-1]:.2f}, {self.diameter_orig[i]:.2f}, {self.diameter_orig[i+1]:.2f}')
            except IndexError:
                pass


    def save_plot_and_data(self):
        outfile_pdf = self.infile.replace('.txt', f'__bw_ord_{self.slider_bw_ord.get()}__bw_fc_{self.slider_bw_fc.get():.2f}.pdf')
        plt.savefig(outfile_pdf, format='pdf', bbox_inches='tight')
        print(f'Speichere Plot unter {outfile_pdf} ab.')

        # Daten zum Plot speichern
        outfile_txt = outfile_pdf.replace('.pdf', '.txt')
        df_neu = pd.DataFrame({'Druck / mbar': self.pressure_raw,
                               'Durchmesser / mm': self.diameter_raw,
                               'Versuchslaufzeit / s': self.time,
                               'Druck (geglaettet) / mbar': self.pressure_filtered,
                               'Durchmesser (geglaettet) / mm': self.diameter_filtered})
        df_neu.to_csv(outfile_txt, sep=';', encoding='utf-8', index=False, header=True)
        print(f'Speichere Daten der Auswertung in {outfile_txt} ab.')
        tk.messagebox.showinfo(title='Output', message=f'Speichere Daten der Auswertung in {outfile_txt} ab.')


    def reset_values(self):
        self.slider_bw_ord.set(self.bw_ord_init)
        self.slider_bw_fc.set(self.bw_fc_init)


    def destructor(self):
        # close plot, close connection to webcam and destroy webcam window
        plt.close()
        self.win.destroy()


app = Application()
app.win.mainloop()
