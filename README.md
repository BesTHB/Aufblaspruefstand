[![DOI:10.1016/j.polymertesting.2023.108273](http://img.shields.io/badge/DOI-10.1016/j.polymertesting.2023.108273-1082c2.svg)](https://doi.org/10.1016/j.polymertesting.2023.108273)

## Installation
***Die folgende Anleitung bezieht sich auf die Windows PowerShell***

Virtuelle Python-Umgebung für PySide6 anlegen
```
python -m venv .\py_venv
```

Virtuelle Python-Umgebung aktivieren
```
.\py_venv\Scripts\Activate.ps1
```

Test, ob Verknüpfung zur virtuellen Python-Umgebung richtig ist
```
Get-Command python
Get-Command pip
```

Pakete aus der requirements.txt installieren
```
pip install -r requirements.txt
```


## Dateien
- Aufblaspruefstand_GUI.ui:  wird mit Qt Designer geöffnet/editiert und enthält die GUI
- Aufblaspruefstand_GUI.py:  wird mittels `pyside6-uic Aufblaspruefstand_GUI.ui -o Aufblaspruefstand_GUI.py` erzeugt und kann anschließend in Aufblaspruefstand_main.py importiert werden
- Aufblaspruefstand_main.py: hier sind die eigentlichen Funktionen der App implementiert und kann mittels `python Aufblaspruefstand_main.py` ausgeführt werden (venv aktivieren!)


## GUI-Entwicklung
Der Qt Designer befindet sich unter folgender Adresse und kann ausgeführt werden, ohne dass die virtuelle Python-Umgebung geladen wurde
```
\\PFAD_ZUR\py_venv\Lib\site-packages\PySide6\designer.exe
```

Eine Qt .ui-Datei wird anschließend zu einer .py-Datei übersetzt
```
pyside6-uic [...].ui -o [...].py
```


## App starten
Die App kann entweder mit python aus der Kommandozeile (venv aktivieren!) heraus gestartet werden
```
(.\py_venv\Scripts\Activate.ps1)
python Aufblaspruefstand_main.py
```

oder zu einer eigenständigen Exe kompiliert werden
```
pyinstaller --onefile --noconsole --name Aufblaspruefstand Aufblaspruefstand_main.py
```

Die Flags bedeuten:
- `--onefile`: Eine einzige Datei erzeugen
- `--noconsole`: Neben dem GUI-Fenster soll keine Konsole (für STDOUT, STDERR) geöffnet werden
- `--name`: Name der Exe

Die Exe liegt anschließend im Ordner `./dist/Aufblaspruefstand.exe`
Beim Kompilieren entsteht außerdem eine `Aufblaspruefstand.spec`, mit der man wiederum anschließend die Exe ebenfalls kompilieren kann,
da in ihr die Flags als Einstellungen gespeichert sind:
```
pyinstaller Aufblaspruefstand.spec
```
