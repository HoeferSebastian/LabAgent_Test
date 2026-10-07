```text
█      ███  ████   ███   ████ █████ █   █ █████ 
█     █   █ █   █ █   █ █     █     ██  █   █   
█     █████ ████  █████ █  ██ ████  █ █ █   █   
█     █   █ █   █ █   █ █   █ █     █  ██   █   
█████ █   █ ████  █   █  ███  █████ █   █   █   
```

*Test-Repository für LabAgent - Assistenzsystem für ein Elektroniklabor
(Messgeräte-Ansteuerung, Messabläufe, Simulation, Dokumentation).*

## Inhalt

- `README.md` - diese Datei
- `Index.md` - automatisch generierte Workspace-Übersicht (wird bei
  Verzeichnisänderungen neu erzeugt, manuelle Änderungen gehen verloren)
- `scripts/` - Batch-Hilfsskripte, u. a. für den GitHub-Login über den
  Git Credential Manager

## Workspace-Struktur

| Ordner          | Zweck                                  |
| --------------- | -------------------------------------- |
| `statemachines/`| Statemachine-Definitionen              |
| `protokolle/`   | Zustands-/Messprotokolle               |
| `prozeduren/`   | Prüfprozeduren                         |
| `dokumente/`    | Dokumente (Datenblätter, Handbücher)   |

## Hinweise

- `gcm_trace.log` und `gcm_login_out.txt` sind lokale Ausgabe-/Logdateien
  des Git-Credential-Managers und gehören nicht in die Versionskontrolle.
