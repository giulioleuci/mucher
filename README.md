# mucher
A Python enhanced interface to much.

# Perché mucher
Questo breve script si interfaccia con much (https://eigen-space.org/much/) per generare test a scelta multipla randomizzati, scritti in LaTeX. Il software è in una fase embrionale, privo di molte funzionalità previste, ma già oggi utilizzabile.

I vantaggi rispetto a much sono:
* creazione di un unico file Excel contenente tutte le informazioni sul test
* possibilità di assegnare punti anche alle risposte non date
* creazione di report sulle singole tipologie di domande

Di contro, l'interfaccia fa perdere una specifica funzionalità di much, ovvero la possibilità di assegnare punti differenziati per risposte errate a singole domande.

# Utilizzo


```
usage: mucher.py [-h] -a {c,v} [-f FILENAME] [-n NUMERO] [-c CORRETTE]
                 [-m MISSING] [-i INCORRETTE] [-v VALUTAZIONE] [-s SEED]

optional arguments:
  -h, --help            show this help message and exit
  -a {c,v}, --azione {c,v}
                        [c]rea o [v]aluta un test
  -f FILENAME, --filename FILENAME
                        Nome del file contenente il test
  -n NUMERO, --numero NUMERO
                        Numero di test da creare
  -c CORRETTE, --corrette CORRETTE
                        Punti per risposta corretta
  -m MISSING, --missing MISSING
                        Punti per risposta non data
  -i INCORRETTE, --incorrette INCORRETTE
                        Punti per risposta errata
  -v VALUTAZIONE, --valutazione VALUTAZIONE
                        Nome del file contenente i test da valutare
  -s SEED, --seed SEED  Seme per la randomizzazione
  ```
Di seguito alcune (parziali) istruzioni, per il dettaglio consultare l'esempio nella cartella `example`:
* `filename` contiene il test da generare.
  * Creare una scheda per ogni domanda che si vuole inserire nel test.
  * In ogni scheda, inserire nella prima riga la domanda, nelle quattro righe successive le quattro opzioni di risposte di cui la prima esatta.
  * Se si vogliono creare più varianti della stessa domanda, replicare per ogni variante quanto detto sopra, partendo dalla riga 5, la riga 10 e così via.
* `numero` è il numero di test da generare.
* `corrette`, `missing` e `incorrette` è il punteggio da assegnare per ogni risposta corretta, non data ed errata.
* `valutazione` è il file contenente le risposte degli studenti, generato manualmente a partire dal file `elaborati.xlsx` autogenerato. A tale file aggiungere una colonna contenente le risposte date dagli studenti (il trattino `-` indica una risposta non data) e il loro nome.
* `seed` è un numero necessario a garantire la riproducibilità.

Ad oggi è necessario modificare manualmente il file `exam.tex` per inserire i dati del test quali la data di svolgimento, la classe, eccetera.
