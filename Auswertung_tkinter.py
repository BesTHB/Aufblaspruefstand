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
        if 'Zyklus' in df:
            self.cycle_orig = df['Zyklus'].to_list()
        else:
            self.cycle_orig = None

        # Kopien der Daten anlegen, in denen die Ausreisser entfernt werden sollen.
        # .copy() ist notwendig, da sonst die Originallisten bearbeitet werden
        self.time = self.time_orig.copy()
        self.pressure_raw = self.pressure_orig.copy()
        self.diameter_raw = self.diameter_orig.copy()
        if self.cycle_orig:
            self.cycle_raw = self.cycle_orig.copy()
        else:
            self.cycle_raw = None

        # Daten zu Durchmesser-Ausreissern entfernen
        self.ausreisser_entfernen()

        # Define axis labels
        self.pressure_label = 'Pressure / mbar'
        self.diameter_label = 'Diameter / mm'
        self.time_label = 'Time / s'

        # Define colors for plot
        self.colors = ['tab:blue', 'tab:orange', 'tab:orange', 'tab:orange', 'tab:green', 'tab:green', 'tab:green', 'tab:red', 'tab:red', 'tab:red', 'tab:purple', 'tab:brown', 'tab:olive']

        # initialize plot canvas
        self.fig, self.axs = plt.subplots(3, 1)
        self.fig.tight_layout(pad=1.5)
        self.plot_canvas = FigureCanvasTkAgg(self.fig, master=self.win)  # A tk.DrawingArea
        self.plot_canvas.draw()
        self.plot_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


        # Feld fuer Glaettung
        self.rahmen1 = tk.Frame(self.win)
        self.rahmen1.pack(side='left', fill=tk.X, expand=True)

        # Indices of cycle starts with different load amplitudes -> different coloring
        if self.cycle_raw:
            self.start_cycles = [0]
            for i in range(1, len(self.cycle_raw)):
                if (self.cycle_raw[i] != self.cycle_raw[i-1]):
                    self.start_cycles.append(i)

            self.start_cycles.append(len(self.cycle_raw))
        else:
            self.start_cycles = [0, len(self.time)]  # min. [0, len(self.time)]

        # create sliders for butterworth filter
        self.bw_ord_init = 3
        self.bw_fc_init = 0.12  # < sampling_freq/2 (!)
        self.sampling_freq = 10  # Hz
        self.bw_fs = tk.IntVar()
        self.bw_ord = tk.IntVar()
        self.bw_fc = tk.DoubleVar()
        self.slider_bw_fs = tk.Scale(self.rahmen1, label='sampl. freq', orient='horizontal', from_=1, to=20, resolution=1, variable=self.bw_fs, command=lambda x: self.update_plot())
        self.slider_bw_ord = tk.Scale(self.rahmen1, label='bw_ord', orient='horizontal', from_=1, to=6, resolution=1, variable=self.bw_ord, command=lambda x: self.update_plot())
        self.slider_bw_fc = tk.Scale(self.rahmen1, label='bw_fc', orient='horizontal', from_=0.02, to=self.sampling_freq/2-0.02, resolution=0.02, variable=self.bw_fc, command=lambda x: self.update_plot())
        self.slider_bw_fs.set(self.sampling_freq)
        self.slider_bw_ord.set(self.bw_ord_init)
        self.slider_bw_fc.set(self.bw_fc_init)
        self.slider_bw_fs.pack()
        self.slider_bw_ord.pack()
        self.slider_bw_fc.pack(fill=tk.X)

        # Schieberegler fuer zeitlichen Versatz zwischen Druck und Durchmesser
        self.versatz = tk.IntVar()
        self.slider_versatz = tk.Scale(self.rahmen1, label='Versatz / Einträge', orient='horizontal', from_=0, to=30, resolution=1, variable=self.versatz, command=lambda x: self.update_plot())
        self.slider_versatz.set(0)
        self.slider_versatz.pack(fill=tk.X)

        # create buttons
        self.btn_reset = tk.Button(self.rahmen1, text='Reset', command=self.reset_values)
        self.btn_reset.pack()
        self.btn_save_plot = tk.Button(self.rahmen1, text='Save plot and data', command=self.save_plot_and_data)
        self.btn_save_plot.pack()


        # Feld fuer Yeoh-Fit
        self.rahmen2 = tk.Frame(self.win)
        self.rahmen2.pack(side='left', fill=tk.X, expand=True)

        self.yeoh_checked = tk.IntVar()
        self.yeoh_checkbox = tk.Checkbutton(self.rahmen2, text='Yeoh-Materialmodell', variable=self.yeoh_checked, onvalue=1, offvalue=0, command=lambda: self.update_plot())
        self.yeoh_checkbox.pack()

        self.c1 = tk.DoubleVar()
        self.c2 = tk.DoubleVar()
        self.c3 = tk.DoubleVar()
        self.slider_c1 = tk.Scale(self.rahmen2, label='c1 / 1e-1', orient='horizontal', from_=1, to=10, resolution=0.1, variable=self.c1, command=lambda x: self.update_plot())
        self.slider_c2 = tk.Scale(self.rahmen2, label='c2 / 1e-4', orient='horizontal', from_=-10, to=10, resolution=0.2, variable=self.c2, command=lambda x: self.update_plot())
        self.slider_c3 = tk.Scale(self.rahmen2, label='c3 / 1e-5', orient='horizontal', from_=1, to=10, resolution=0.1, variable=self.c3, command=lambda x: self.update_plot())
        self.slider_c1.set(3.6)
        self.slider_c2.set(1)
        self.slider_c3.set(7.5)
        self.slider_c1.pack(fill=tk.X)
        self.slider_c2.pack(fill=tk.X)
        self.slider_c3.pack(fill=tk.X)


        # Feld fuer Gent-Fit
        self.rahmen3 = tk.Frame(self.win)
        self.rahmen3.pack(side='left', fill=tk.X, expand=True)

        self.gent_checked = tk.IntVar()
        self.gent_checkbox = tk.Checkbutton(self.rahmen3, text='Gent-Materialmodell', variable=self.gent_checked, onvalue=1, offvalue=0, command=lambda: self.update_plot())
        self.gent_checkbox.pack()

        self.mu = tk.DoubleVar()
        self.Jm = tk.DoubleVar()
        self.slider_mu = tk.Scale(self.rahmen3, label='mu', orient='horizontal', from_=0.05, to=10, resolution=0.05, variable=self.mu, command=lambda x: self.update_plot())
        self.slider_Jm = tk.Scale(self.rahmen3, label='Jm', orient='horizontal', from_=30, to=1000, resolution=10, variable=self.Jm, command=lambda x: self.update_plot())
        self.slider_mu.set(0.7)
        self.slider_Jm.set(70)
        self.slider_mu.pack(fill=tk.X)
        self.slider_Jm.pack(fill=tk.X)


        # Feld fuer Geometriewerte fuer Yeoh-/Gent-Fit
        self.rahmen4 = tk.Frame(self.win)
        self.rahmen4.pack(side='left', fill=tk.X, expand=True)
        tk.Label(self.rahmen4, text='Anfangsradius r0').grid(row=0)
        tk.Label(self.rahmen4, text='Anfangsdicke t0').grid(row=1)
        self.spinbox_r0 = tk.Spinbox(self.rahmen4, justify='right', from_=20, to=30, increment=0.2, command=lambda: self.update_plot())
        self.spinbox_t0 = tk.Spinbox(self.rahmen4, justify='right', from_=0.1, to=0.5, increment=0.01, command=lambda: self.update_plot())
        self.spinbox_r0.grid(row=0, column=1)
        self.spinbox_t0.grid(row=1, column=1)


        # update plot
        self.update_plot()


    def calc_p_yeoh(self, c1, c2, c3, r, t0):
        # Streckung
        lmb = r/r[0]

        # 1. Invariante I1 = tr(C) = tr(b)
        I1 = 2*lmb**2 + 1/lmb**4

        # Aus sig_33 != 0 --> p_star = (2/lmb**4) * (c1 + 2*c2*(I1-3) + 3*c3*(I1-3)**2)  # (Lagrange Multiplier)
        # sig_11 = sig_22 = -p_star + (2*lmb**2) * (c1 + 2*c2*(I1-3) + 3*c3*(I1-3)**2)
        sig_11 = 2 * (lmb**2 - 1/lmb**4) * (c1 + 2*c2*(I1-3) + 3*c3*(I1-3)**2)

        # Materialvolumenerhaltung aus Inkompressibilitaet --> aktuelle Dicke
        t = t0/lmb**2  # = t0*(r[0]/r)**2

        # sig_11 != sig_t = r*p/(2*t)   ("Kesselformel")
        p = sig_11*2*t/r  # MPa = 10^1 bar = 10^4 mbar
        p = p*10000  # mbar

        return p, lmb


    def calc_p_gent(self, mu, Jm, r, t0):
        # Streckung
        lmb = r/r[0]

        # 1. Invariante I1 = tr(C) = tr(b)
        I1 = 2*lmb**2 + 1/lmb**4

        # Aus sig_33 != 0 --> p_star = (1/lmb**4) * mu*Jm/(Jm-I1+3)  # (Lagrange Multiplier)
        # sig_11 = sig_22 = -p_star + lmb**2 * mu*Jm/(Jm-I1+3)
        sig_11 = (lmb**2 - 1/lmb**4) * mu*Jm/(Jm-I1+3)

        # Materialvolumenerhaltung aus Inkompressibilitaet --> aktuelle Dicke
        t = t0/lmb**2  # = t0*(r[0]/r)**2

        # sig_11 != sig_t = r*p/(2*t)   ("Kesselformel")
        p = sig_11*2*t/r  # MPa = 10^1 bar = 10^4 mbar
        p = p*10000  # mbar

        return p, lmb


    def update_plot(self):
        # set upper limit for fc slider, which has to be < sampling_freq/2
        self.slider_bw_fc.configure(to=self.slider_bw_fs.get()/2-0.02)

        # apply lowpass digital Butterworth filter to raw measurements of pressure and diameter
        b, a = signal.butter(self.slider_bw_ord.get(), self.slider_bw_fc.get(), 'low', analog=False, fs=self.slider_bw_fs.get())
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
            # "-1"-cycles will be white, all other cycles will have a different color
            if self.cycle_raw:
                tmp_cycle = self.cycle_raw[self.start_cycles[i]]
                if tmp_cycle != -1:
                    color = self.colors[tmp_cycle+1]  # +1, weil Liste mit Farben mit tab:blue beginnt, was bereits fuer die ungefilterte Kurve benutzt wird
                else:
                    color = 'w'
            else:
                color = 'tab:orange'

            idx0 = self.start_cycles[i]
            idx1 = self.start_cycles[i+1]+1  # +1, damit bis zum Start des Folgezyklus geplottet wird

            self.axs[0].plot(self.time[idx0:idx1], self.pressure_filtered[idx0:idx1], c=color)
            self.axs[1].plot(self.time[idx0:idx1], self.diameter_filtered[idx0:idx1], c=color)
            self.axs[2].plot(self.diameter_filtered[idx0:idx1], self.pressure_filtered[idx0:idx1], c=color)

        # Versatz
        v = self.slider_versatz.get()
        if v != 0:
            self.axs[2].plot(self.diameter_filtered[v:], self.pressure_filtered[:-v], c='tab:orange', ls='dashed', label='Versatz')

        r0 = float(self.spinbox_r0.get())
        self.r = np.linspace(r0, 4*r0, 1000)
        self.t0 = float(self.spinbox_t0.get())

        # Falls aktiviert, plotte Yeoh-Fit
        if self.yeoh_checked.get() == 1:
            p_yeoh, _ = self.calc_p_yeoh(self.slider_c1.get()*1e-1, self.slider_c2.get()*1e-4, self.slider_c3.get()*1e-5, self.r, self.t0)
            self.axs[2].plot(2*self.r, p_yeoh, color='gray', ls='dashed', label='Yeoh')

        # Falls aktiviert, plotte Gent-Fit
        if self.gent_checked.get() == 1:
            p_gent, _ = self.calc_p_gent(self.slider_mu.get(), self.slider_Jm.get(), self.r, self.t0)
            self.axs[2].plot(2*self.r, p_gent, color='gray', ls='dotted', label='Gent')

        self.axs[0].set_ylabel(self.pressure_label)
        self.axs[1].set_xlabel(self.time_label)
        self.axs[1].set_ylabel(self.diameter_label)
        self.axs[2].set_xlabel(self.diameter_label)
        self.axs[2].set_ylabel(self.pressure_label)
        self.axs[0].locator_params(axis='y', nbins=5)  # create 5 ticks on y-axis
        self.axs[1].locator_params(axis='y', nbins=5)
        self.axs[2].locator_params(axis='y', nbins=5)

        # Zeige Legende, falls Labels vorhanden
        h, l = self.axs[2].get_legend_handles_labels()
        if h:
            self.axs[2].legend(h, l)

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
            if self.cycle_raw:
                del self.cycle_raw[i]
            del self.time[i]

            try:
                print(f'Index {i-1},{i},{i+1}: {self.diameter_orig[i-1]:.2f}, {self.diameter_orig[i]:.2f}, {self.diameter_orig[i+1]:.2f}')
            except IndexError:
                pass


    def save_plot_and_data(self):
        outfile_pdf = self.infile.replace('.txt', f'__ohneAusreisser__bw_ord_{self.slider_bw_ord.get()}__bw_fc_{self.slider_bw_fc.get():.2f}__bw_fs_{self.slider_bw_fs.get()}.pdf')
        plt.savefig(outfile_pdf, format='pdf', bbox_inches='tight')
        print(f'Speichere Plot unter {outfile_pdf} ab.')

        # Daten zum Plot speichern
        outfile_txt = outfile_pdf.replace('.pdf', '.txt')
        if self.cycle_raw:
            df_neu = pd.DataFrame({'Druck / mbar': self.pressure_raw,
                                'Durchmesser / mm': self.diameter_raw,
                                'Zyklus': self.cycle_raw,
                                'Versuchslaufzeit / s': self.time,
                                'Druck (geglaettet) / mbar': self.pressure_filtered,
                                'Durchmesser (geglaettet) / mm': self.diameter_filtered})
        else:
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
