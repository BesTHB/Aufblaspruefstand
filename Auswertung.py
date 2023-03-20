import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy import signal


data_dir = './Messungen/2023_03_17__11_12_12/'   # '/' AM ENDE!

# Daten einlesen.
# Wichtig: Die Spalten in beiden Dateien, die den Zeitstempel der Messungen enthalten, muessen gleich heissen!
# Damit die Zeitstempel richtig erkannt werden, wird die entsprechende Spalte mit parse_dates bearbeitet.
df_druck = pd.read_csv(data_dir+'Druck.txt', sep=';', decimal='.', header=0, parse_dates=['Zeitpunkt Messung'])
df_durchmesser = pd.read_csv(data_dir+'Durchmesser.txt', sep=';', decimal=',', header=0, parse_dates=['Zeitpunkt Messung'])

# Da die Durchmesser ggf. vom dtype "object" sind, werden hier vorsichtshalber beide Spalten in float umgewandelt.
df_druck['Druck / mbar'] = df_druck['Druck / mbar'].astype(float)
df_durchmesser['Durchmesser / mm'] = df_durchmesser['Durchmesser / mm'].astype(float)

print(df_druck)
print(df_durchmesser)

print(df_druck.dtypes)
print(df_durchmesser.dtypes)

# Hier werden die Messungen zeitlich verknuepft, und zwar immer die zeitlich nahe liegendsten Druck- und Durchmessermessungen.
# Es werden die Zeitstempel des erst genannten DataFrames beibehalten (hier: df_druck).
df_merged = pd.merge_asof(df_druck, df_durchmesser, on='Zeitpunkt Messung', direction='nearest')
print(df_merged)

# Von allen Zeitstempeln wird der erste Zeitstempel abgezogen, um die Versuchslaufzeit zu berechnen.
# Anschliessend wird die Versuchslaufzeit in Sekunden umgewandelt.
versuchslaufzeit = df_merged['Zeitpunkt Messung'] - df_merged['Zeitpunkt Messung'][0]
df_merged['Versuchslaufzeit / s'] = versuchslaufzeit.dt.total_seconds()
print(df_merged)

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

plt.savefig(data_dir+'Auswertung.png', format='png', bbox_inches='tight')
plt.show()