# CUSTOM MTURK FRAMEWORK

WIP

## Description:

WIP

## Features:

WIP

## Installation

```bash
WIP bash-script
```

## TODO Stand 03.07.2019 13:27(WIP)

### Frontend
 #### 1. Priorität Erforderlich 
  * Füge Finish-Seite mit Überblick, Kosten und HTML-Vorschau ein
  * Füge Buttons für jede HITRow und MiniHITRow im Dashboard ein: HIT/MiniHIT abbrechen, Pausieren/Fortsetzen, Worker anzeigen, CSV-Import, CSV-Export, Preis ändern(?)
  * Implementiere eine Workerübersicht im Dashboard
 #### 2. Priorität Hoch 
  * Füge ein Overlay (Bootstrap Modal) für das CSV-Import und CSV-Export ein.
  * Remake/Polish die MiniHIT-Gruppierung des Dashboards
 #### 3. Priorität Mittel
  * ~~Zeige akzeptierte Worker hinter Fortschritt-Spalte an~~ Anm: Pending hinter Fortschritt
 #### 4. Priorität Niedrig 
  * Layout aktualisieren und gestrichene Funktionen entfernen
  * ~~Mache HIT-OverviewChild im Dashboard suchbar~~
  * Style weniger hässlich machen
 

### Backend
 #### 1. Priorität Erforderlich 
  * ~~Schedulerfunktion testen~~
  * Implementiere eine automatische Qualifikationsvergabe für Worker nach Bearbeitung eines MiniHITs
  * Implementiere einen CSV-Import und -Export zum Akzeptieren, Ablehnen, Bonus zahlen und Softblocken inkl. ApiCalls
  * ~~Restrukturiere Dashboard, sodass zusammengehörige MiniHITs gruppiert mit Overview-Reihe angezeigt werden~~
 #### 2. Priorität Hoch
  * Refactor die order-list für das Dashboard
 #### 3. Priorität Mittel
  * ~~Refactor den ganzen blöden Code~~
 #### 4. Priorität Niedrig
  * Refactor den Code weiter
  * ~~Lösche die StartDate Felder~~
  * requirements.txt aktualisieren und unnötige Packages rausschmeißen