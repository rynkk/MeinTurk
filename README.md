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

## TODO Stand 12.07.2019 14:12(WIP)

### Frontend
 #### 1. Priorität Erforderlich 
  * Füge Finish-Seite mit Überblick, Kosten und HTML-Vorschau ein
  * ~~Füge Buttons für jede HITRow und MiniHITRow im Dashboard ein: HIT/MiniHITabbrechen, Pausieren/Fortsetzen, Worker anzeigen, CSV-Import, CSV-Export, Preis ändern(?)~~
  * ~~Implementiere eine Workerübersicht im Dashboard~~ Erledigt für MiniHITs, TODO für batches
 #### 2. Priorität Hoch 
  * ~~Füge ein Overlay (Bootstrap Modal) für das CSV-Import und CSV-Export ein.~~
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
  * ~~Implementiere eine automatische Qualifikationsvergabe für Worker nach Bearbeitung eines MiniHITs~~
  * ~~Implementiere einen CSV-Import und -Export zum Akzeptieren, Ablehnen, Bonus zahlen und Softblocken inkl. ApiCalls~~
  * ~~Restrukturiere Dashboard, sodass zusammengehörige MiniHITs gruppiert mit Overview-Reihe angezeigt werden~~
 #### 2. Priorität Hoch
  * Refactor die order-list für das Dashboard
 #### 3. Priorität Mittel
  * ~~Refactor den ganzen blöden Code~~
 #### 4. Priorität Niedrig
  * Refactor den Code weiter
  * ~~Lösche die StartDate Felder~~
  * requirements.txt aktualisieren und unnötige Packages rausschmeißen

### Bugs
 #### ~~DB-IntegrityError~~
  1. ~~Reproduzieren:~~
   * ~~Erstelle mehrere batched surveys mit gleichem Namen, Beschreibung und Description (Rest so lassen) und erstelle den HIT~~
  2. ~~Warum:~~
   * ~~HITs werden über die HITTypeId organisiert~~
   * ~~HITTypeIds sind nicht einzigartig sondern kommen öfter vor, wenn die gleichen Parameter für CreateHITType gewählt werden~~
   * ~~HITs können bei mehreren gleichen HITTypeIds nicht eindeutig über diese organisiert werden~~
  3. ~~Fix:~~
   * ~~Benutze statt HITTypeIds eine eindeutige selbstgenerierte ID (sqlalchemy bietet sich an) und speicher sie in der RequesterAnnotation jedes batchedHits~~