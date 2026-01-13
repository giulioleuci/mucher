# Mucher

**Mucher** è un'interfaccia Python avanzata per [much](https://eigen-space.org/much/), il generatore di test a scelta multipla randomizzati in LaTeX.

## Indice
- [Cos'è Mucher](#cosè-mucher)
- [Funzionalità](#funzionalità)
- [Interazione con much](#interazione-con-much)
- [Requisiti](#requisiti)
- [Installazione](#installazione)
- [Utilizzo](#utilizzo)
- [Struttura del file Excel](#struttura-del-file-excel)
- [File di configurazione YAML](#file-di-configurazione-yaml)
- [Esempi](#esempi)

## Cos'è Mucher

Mucher è un wrapper Python che estende le capacità di **much** (Multiple Choice), un tool per la generazione di test randomizzati. Much genera varianti di test a scelta multipla con domande e risposte mescolate casualmente, producendo output in formato LaTeX compilabile in PDF.

### Vantaggi rispetto a much

- ✅ **Gestione centralizzata**: Un unico file Excel per tutte le domande (invece di file separati per ogni domanda)
- ✅ **Punteggio flessibile**: Possibilità di assegnare punti anche alle risposte non date
- ✅ **Sistema di valutazione integrato**: Correzione automatica dei test con calcolo punteggi
- ✅ **Report dettagliati**: Analisi statistica per categoria di domande
- ✅ **Visualizzazioni grafiche**: Grafici a barre per l'analisi delle risposte
- ✅ **Configurazione YAML**: Gestione semplificata delle impostazioni
- ✅ **Logging strutturato**: Tracciamento dettagliato delle operazioni

### Limitazioni rispetto a much

- ⚠️ Mucher non supporta la funzionalità di much per assegnare punti differenziati per risposte errate a singole domande specifiche

## Funzionalità

### 1. Generazione Test (Modalità Creazione)

Il modulo `ExamGenerator` gestisce l'intero processo di generazione:

1. **Parsing domande da Excel**
   - Legge domande organizzate per categoria (ogni scheda Excel = una categoria)
   - Prima riga = intestazione, righe successive = varianti della domanda
   - Supporta numero variabile di risposte per ogni domanda
   - La prima risposta è sempre quella corretta

2. **Conversione formato much**
   - Crea file di domande nel formato richiesto da much (testo + risposte separate da ".")
   - Genera il file `description` con le direttive per much

3. **Invocazione much**
   - Esegue much con il seed configurato per garantire riproducibilità
   - Genera `mc-output.tex` con le varianti randomizzate
   - Crea `mc-serials.txt` con i numeri seriali e le risposte corrette

4. **Compilazione LaTeX**
   - Genera il template LaTeX `exam.tex`
   - Compila con `pdflatex` per produrre il PDF finale
   - Gestisce immagini (JPG, PNG, GIF, JPEG)

5. **Output**
   - `exam.pdf`: PDF con tutte le varianti del test
   - `exam.tex`: Sorgente LaTeX
   - `elaborati.xlsx`: File Excel con numeri seriali e risposte corrette

### 2. Valutazione Test (Modalità Grading)

Il modulo `ExamGrader` corregge i test:

1. **Caricamento risposte**
   - Legge il file Excel con le risposte degli studenti
   - Valida la struttura del file

2. **Calcolo punteggi**
   - Confronta risposte date con risposte corrette
   - Applica i punteggi configurati:
     - Risposta corretta: punti configurati (default: 4)
     - Risposta non data (indicata con `-`): punti configurati (default: 1)
     - Risposta errata: punti configurati (default: 0)

3. **Report per categoria**
   - Conta risposte corrette, non date ed errate per ogni categoria di domande
   - Identifica le aree più problematiche

4. **Output**
   - File Excel con colonna PUNTEGGI aggiunta
   - Dizionario con statistiche per categoria

### 3. Generazione Report Visivi

Il modulo `ReportGenerator` crea visualizzazioni:

1. **Grafico a barre impilate**
   - Mostra distribuzione risposte per categoria
   - Tre segmenti: corrette (blu), non date (grigio), errate (oliva)
   - Salvataggio in formato PNG ad alta risoluzione (150 DPI)

### 4. Gestione Configurazione

La classe `ExamConfig` supporta:

- Configurazione tramite file YAML
- Override parametri da linea di comando
- Validazione parametri
- Valori di default sensati

## Interazione con much

Mucher si interfaccia con much nel seguente modo:

### 1. Formato file domande

Much richiede file di testo con formato specifico:
```
Testo della domanda
.
Prima risposta (corretta)
.
Seconda risposta
.
Terza risposta
.
[altre risposte...]
.
```

Mucher converte automaticamente ogni riga del file Excel (esclusa l'intestazione) in questo formato, supportando un numero variabile di risposte.

### 2. File description

Mucher genera il file `description` che contiene le direttive per much:

```
directory ".";              # Directory dei file domande
seed 42;                    # Seed per randomizzazione (riproducibilità)
serial 10;                  # Numero seriale iniziale
use 1 from "categoria1-*";  # Quante domande usare da categoria1
use 1 from "categoria2-*";  # Quante domande usare da categoria2
create 30;                  # Numero di varianti da creare
```

### 3. Comandi much utilizzati

Mucher invoca much con input interattivo:
- `c`: modalità creazione
- `description`: nome del file di descrizione

### 4. Output di much

Much genera:
- `mc-output.tex`: File LaTeX con tutte le varianti (usa macro `\mcserialnumber`, `\mcquestionnumber`)
- `mc-serials.txt`: Tabella con numeri seriali, domande selezionate e risposte corrette

### 5. Funzionalità much utilizzate

- **Randomizzazione controllata**: Il seed garantisce che la stessa configurazione produca sempre gli stessi test
- **Serializzazione**: Ogni variante ha un numero identificativo univoco
- **Shuffling**: Domande e risposte vengono mescolate casualmente
- **Selezione da pool**: Possibilità di usare N domande da un pool più ampio (es. 1 domanda da 5 varianti)

### 6. Funzionalità much NON utilizzate

- Punti differenziati per singole risposte errate (much permette di specificare penalità diverse per ogni risposta sbagliata di una domanda specifica)

## Requisiti

### Software richiesto

1. **Python 3.7+**
2. **much** - [https://eigen-space.org/much/](https://eigen-space.org/much/)
3. **pdflatex** - Distribuzione LaTeX completa (TeX Live, MiKTeX, etc.)

### Dipendenze Python

```
pandas>=1.3.0        # Gestione file Excel e dati tabulari
matplotlib>=3.4.0    # Generazione grafici
jinja2>=3.0.0        # Template engine (per future estensioni)
PyYAML>=6.0          # Parsing file YAML
openpyxl>=3.0.0      # Lettura/scrittura file Excel .xlsx
```

## Installazione

```bash
# Clona il repository
git clone https://github.com/giulioleuci/mucher.git
cd mucher

# Installa dipendenze Python
pip install -r requirements.txt

# Installa much (esempio per sistemi Debian/Ubuntu)
# Verifica le istruzioni specifiche su https://eigen-space.org/much/
```

## Utilizzo

### Sintassi generale

```
usage: mucher.py [-h] -a {c,v} [-f FILENAME] [-n NUMERO] [-c CORRETTE]
                 [-m MISSING] [-i INCORRETTE] [-v VALUTAZIONE] [-s SEED]
                 [--config CONFIG] [--generate-config] [--no-cleanup]
                 [--verbose]

Mucher - Enhanced wrapper for the much exam generator

optional arguments:
  -h, --help            Mostra questo messaggio di aiuto
  -a {c,v}, --azione {c,v}
                        Action: [c]reate o [v]alidate/grade exams
  -f FILENAME, --filename FILENAME
                        File Excel con le domande (default: questionario.xlsx)
  -n NUMERO, --numero NUMERO
                        Numero di varianti da generare (default: 30)
  -c CORRETTE, --corrette CORRETTE
                        Punti per risposta corretta (default: 4)
  -m MISSING, --missing MISSING
                        Punti per risposta non data (default: 1)
  -i INCORRETTE, --incorrette INCORRETTE
                        Punti per risposta errata (default: 0)
  -v VALUTAZIONE, --valutazione VALUTAZIONE
                        File Excel con risposte studenti (default: elaborati.xlsx)
  -s SEED, --seed SEED  Seed per randomizzazione (default: 42)
  --config CONFIG       File di configurazione YAML
  --generate-config     Genera template configurazione YAML
  --no-cleanup          Non eliminare file temporanei
  --verbose             Abilita logging dettagliato
```

## Struttura del file Excel

### File domande (questionario.xlsx)

- **Una scheda per categoria**: Ogni scheda Excel rappresenta una categoria di domande
- **Prima riga = intestazione**: Intestazione per leggibilità umana con le colonne:
  - `Testo della domanda`
  - `Risposta corretta`
  - `Alternativa 1`, `Alternativa 2`, `Alternativa 3`, ...
  - `Numero Colonne Alternative` (ultima colonna)
- **Righe successive = varianti**: Ogni riga (dalla seconda in poi) rappresenta una variante della domanda
- **Numero variabile di risposte**: Ogni domanda può avere un numero diverso di risposte, specificato nell'ultima colonna

**Esempio scheda "Vettori":**

| Testo della domanda | Risposta corretta | Alternativa 1 | Alternativa 2 | Alternativa 3 | Numero Colonne Alternative |
|---------------------|-------------------|---------------|---------------|---------------|----------------------------|
| Quali sono le tre caratteristiche che definiscono un vettore? | Modulo, direzione e verso | Lunghezza, verso e unità di misura | Intensità, retta e punto | Valore, segno e unità di misura | 4 |
| Un ente definito da modulo, direzione e verso è: | Un vettore | Uno scalare | Un numero puro | Una costante | 4 |
| Per descrivere completamente un vettore nel piano occorrono: | Modulo, direzione e verso | Modulo, direzione e unità di misura | Intensità, retta e punto | Intensità, direzione e unità di misura | 4 |

**Esempio con numero variabile di risposte:**

| Testo della domanda | Risposta corretta | Alternativa 1 | Alternativa 2 | Alternativa 3 | Numero Colonne Alternative |
|---------------------|-------------------|---------------|---------------|---------------|----------------------------|
| La somma massima di due vettori si ha quando sono: | Paralleli e concordi | Perpendicolari | Opposti | Casuali | 4 |
| La somma minima di due vettori si ha quando sono: | Paralleli e discordi | Paralleli e concordi | Perpendicolari | | 3 |
| Se il modulo risultante è la somma dei moduli, l'angolo è: | $0^\circ$ | $180^\circ$ | $90^\circ$ | $45^\circ$ | 4 |

**Note:**
- La colonna `Numero Colonne Alternative` indica il numero totale di risposte (risposta corretta + alternative)
- Se una domanda ha solo 3 risposte, lasciare vuote le colonne delle alternative non utilizzate e indicare `3` nell'ultima colonna
- Le formule LaTeX (es. `$0^\circ$`) sono supportate nel testo delle domande e delle risposte

### File risposte studenti

Partire dal file `elaborati.xlsx` autogenerato e aggiungere:
- Colonna con le risposte date dagli studenti (A, B, C, D, o `-` per non data)
- Colonna con i nomi degli studenti

## File di configurazione YAML

Crea un file di configurazione per evitare di passare parametri da linea di comando:

```bash
# Genera template
python mucher.py --generate-config

# Modifica mucher_config.yaml a piacimento
```

Esempio `mucher_config.yaml`:
```yaml
question_file: questionario.xlsx
num_tests: 30
serial_start: 10
usage_per_category: 1
seed: 42
points_correct: 4
points_missing: 1
points_incorrect: 0
results_file: elaborati.xlsx
output_dir: .
cleanup_temp: true
```

## Esempi

### Generare 30 varianti di test

```bash
python mucher.py -a c -f questionario.xlsx -n 30 -s 42
```

### Generare test con punteggi personalizzati

```bash
python mucher.py -a c -f domande.xlsx -n 25 -c 3 -m 0 -i -1
```
(3 punti per corrette, 0 per non date, -1 per errate)

### Valutare risposte studenti

```bash
python mucher.py -a v -v elaborati_con_risposte.xlsx
```

Questo genera:
- `elaborati_con_risposte_corretti.xlsx` con punteggi
- `valutazioni_analisi_risposte.png` con grafici

### Usare file di configurazione

```bash
python mucher.py -a c --config config.yaml
```

### Debug con file temporanei

```bash
python mucher.py -a c -f test.xlsx --no-cleanup --verbose
```

## Note

- È necessario modificare manualmente il file `exam.tex` generato per inserire intestazioni specifiche (data, classe, tempo a disposizione, ecc.)
- Assicurarsi che il file Excel non contenga celle vuote o formattazione inattesa
- Il seed garantisce riproducibilità: stesso seed = stesso test
- Per esempi completi, consultare la cartella `example/`
