# pong-headless (AppContainer-Export)

Auszug des LabAgent-AppContainers **`pong-headless`** (Id `ac-ddbc4f45`, Version 5,
Status *Freigegeben*) unter Versionskontrolle.

> Der AppContainer selbst ist **kein Git-Objekt**: Er liegt im LabAgent-Store
> (`appcontainers.db`). Dieses Verzeichnis versioniert nur seine Bestandteile
> (Quelltext + Metadaten), damit die Sandbox-Konfiguration nachvollziehbar bleibt.

## Inhalt

| Datei | Zweck |
| --- | --- |
| `main.py` | Programm des Containers, byte-identisch zur Store-Version 5 (sha256 `4471ffec…f967b`, 10 965 Byte) |
| `container.json` | Container-Metadaten (Id, Version, Einstiegspunkt, Limits, Netz, Tags, Datei-Hash) |

## Eigenschaften

- Reines Python 3, **nur Standardbibliothek**, keine Pip-Pakete
- **Kein Netzwerkzugriff**, keine Display-Ausgabe (headless, ASCII-Rendering)
- Limits: 120 s / 256 MB / 1 CPU / 64 Prozesse / 256 MB Disk / 256 kB Ausgabe
- Einstiegspunkt: `main.py` (liest JSON-Konfiguration von `stdin`)

## Starten

Lokal (auf dem Host, Ausgabeordner `out/` wird selbst angelegt):

```
python main.py < input.json
```

In der Sandbox über den LabAgent-Container:

```
appcontainer_run("pong-headless", inputJson='{"seed": 7, "max_points": 11}')
```

## Eingabe (`stdin`, JSON, alle Felder optional)

| Feld | Default | Bedeutung |
| --- | --- | --- |
| `seed` | 7 | Zufallsstartwert |
| `max_points` | 11 | Punkte bis Spielende |
| `difficulty` | 0.5 | globaler Schwierigkeits-/Fehlerfaktor |
| `max_steps` | 60000 | Sicherheitslimit an Simulationsschritten |
| `sample_every` | 300 | jedes n-te Frame in den Bericht aufnehmen |
| `show_frames` | 3 | Anzahl der im Bericht gezeigten ASCII-Frames |
| `left_err` | 3.0 | Zielfehler des linken (KI-)Schlägers |
| `left_gain` | 0.9 | Regelverstärkung links |
| `right_err` | 6.0 | Zielfehler des rechten (KI-)Schlägers |
| `right_gain` | 1.0 | Regelverstärkung rechts |
| `right_refresh` | 4 | Neuberechnung des rechten Ziels alle n Schritte |

## Ausgabe

- `out/result.json` – Statistik des Spiels (Punktestand, Schrittzahl, Kenngrößen)
- `out/pong_replay.txt` – ASCII-Frames des Spielverlaufs
