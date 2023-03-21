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
        self.win.protocol('WM_DELETE_WINDOW', self.destructor)

        # Read data
        #self.infile = './Messungen/TIME_STAMP/Auswertung.txt'
        self.infile = 'E:/Seafile/paper_PolymerTesting/LaTeX2/data/2023_03_21__09_11_35/Auswertung.txt'
        df = pd.read_csv(self.infile, sep=';', decimal='.', header=0)

        # Save data in separate lists
        self.time = df['Versuchslaufzeit / s'].to_numpy()
        self.pressure_raw = df['Druck / mbar'].to_numpy()
        self.diameter_raw = df['Durchmesser / mm'].to_numpy()

        # Define axis labels
        self.pressure_label = 'Pressure / mbar'
        self.diameter_label = 'Diameter / mm'
        self.time_label = 'Time / s'

        # Define colors for plot
        self.blue = '#1f77b4'
        self.orange = '#ff7f0e'

        # initialize plot canvas
        self.fig, self.axs = plt.subplots(3, 1)
        self.fig.tight_layout(pad=1.5)
        self.plot_canvas = FigureCanvasTkAgg(self.fig, master=self.win)  # A tk.DrawingArea
        self.plot_canvas.draw()
        self.plot_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

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
        self.btn_save_plot = tk.Button(self.win, text='Save plot', command=self.save_plot)
        self.btn_save_plot.pack()

        # update plot
        self.update_plot()


    def update_plot(self):
        # Butterworth-Filter anwenden, um Druck- und Durchmessermessung zu glaetten
        b, a = signal.butter(self.slider_bw_ord.get(), self.slider_bw_fc.get(), 'low', analog=False, fs=self.sampling_freq)
        w, h = signal.freqs(b, a)
        pressure_filtered = signal.filtfilt(b, a, self.pressure_raw)
        diameter_filtered = signal.filtfilt(b, a, self.diameter_raw)

        # clear plot
        self.axs[0].clear()
        self.axs[1].clear()
        self.axs[2].clear()

        # new plot
        self.axs[0].plot(self.time, self.pressure_raw, c=self.blue)
        self.axs[0].plot(self.time, pressure_filtered, c=self.orange)
        self.axs[1].plot(self.time, self.diameter_raw, c=self.blue)
        self.axs[1].plot(self.time, diameter_filtered, c=self.orange)
        self.axs[2].plot(diameter_filtered, pressure_filtered, c=self.orange)

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


    def save_plot(self):
        outfile_pdf = self.infile.replace('.txt', f'__bw_ord_{self.slider_bw_ord.get()}__bw_fc_{self.slider_bw_fc.get():.2f}.pdf')
        plt.savefig(outfile_pdf, format='pdf', bbox_inches='tight')
        print(f'Speichere Plot unter {outfile_pdf} ab.')


    def reset_values(self):
        self.slider_bw_ord.set(self.bw_ord_init)
        self.slider_bw_fc.set(self.bw_fc_init)


    def destructor(self):
        # close plot, close connection to webcam and destroy webcam window
        plt.close()
        self.win.destroy()


app = Application()
app.win.mainloop()
