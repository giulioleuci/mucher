import jinja2
from jinja2 import Template
import os
import pandas as pd
import itertools
import random
from random import shuffle
import numpy as np
import matplotlib.pyplot as plt
import pprint
import sys
import argparse
import subprocess
import shutil
from math import isnan
import collections
from time import sleep

pp = pprint.PrettyPrinter(indent=4)

latex_jinja_env = jinja2.Environment(
    block_start_string = '\BLOCK{',
    block_end_string = '}',
    variable_start_string = '\VAR{',
    variable_end_string = '}',
    comment_start_string = '\#{',
    comment_end_string = '}',
    line_statement_prefix = '%%',
    line_comment_prefix = '%#',
    trim_blocks = True,
    autoescape = False,
    loader = jinja2.FileSystemLoader(os.path.abspath('.'))
    )


# # Definizione delle funzioni

# ## Introduzione


def Exam_Template():
    template = """
\\documentclass[11pt,a4paper]{article}
\\usepackage{amsfonts,latexsym}
\\usepackage[italian]{babel}
\\usepackage{amsfonts}
\\usepackage{amsmath}
\\usepackage{amssymb}
\\usepackage{fullpage}
\\usepackage{graphicx}
\\usepackage{wrapfig}
\\usepackage{siunitx}
\\usepackage{physics}
\\usepackage{multicol}
\\usepackage{geometry}
\\usepackage{microtype}
\\usepackage{siunitx}
\\usepackage{physics}
\\usepackage{multicol}

\\geometry{top=0.7cm, bottom=0.7cm, left=1cm, right=1cm}

\\begin{document}

\\pagestyle{empty}

\\newcommand{\\mcglobalheader}{
}

\\newcommand{\\boxt}{{\\Huge $\\square$ }}

\\newcommand{\\mcpaperheader}{
\ \\
TESTO NUMERO \mcserialnumber. STUDENTE: \\\\
{\\textbf{Tempo a disposizione: XXXX.} In ognuna delle seguenti domande una sola opzione è corretta.
\\\ Risposta corretta: XX punti. Risposta non data: XX punti. Risposta errata: XX punti.}

\\begin{center}
{\\Large Verifica di XXX n.XX: XXXX}\\
Classe XX, XX/XX/20XX.
\\end{center}
}



\\newcommand{\\mcpaperfooter}{



\\newpage
}

\\newcommand{\\mcquestionheader}{\\noindent{\\bf \\mcquestionnumber}. }

\\newcommand{\\mcquestionfooter}{}

\\input mc-output.tex

\\end{document}
    """
    return template


# ## Genera file

def Genera_Tex(folder='.', filename="exam.tex"):
    with open(os.path.join(folder,filename),'w') as file:
        print(latex_jinja_env.from_string(Exam_Template()).render(),file=file)
    return

def Genera_file_domande(filename='questionario.xlsx',folder='.'):
    df = pd.ExcelFile(filename)

    sheets = df.sheet_names

    for sheet in sheets:
        elems = df.parse(sheet, header=None).values
        if len(elems)==5:
            name = os.path.join(folder,sheet+"-0")
            question = elems[0][0].strip()
            responses = [str(e[0]).strip() for e in elems[1:]]
            responses = "\n.\n".join(responses)
            with open(name,'w') as file:
                print(question+"\n.\n"+responses+"\n.\n",file=file)
        else:
            n = int(len(elems)/5)
            for i in range(n):
                name = os.path.join(folder,sheet+"-"+str(i))
                question = elems[5*i][0].strip()
                responses = [str(e[0]).strip() for e in elems[5*i+1:5*i+1+4]]
                responses = "\n.\n".join(responses)
                with open(name,'w') as file:
                    print(question+"\n.\n"+responses+"\n.\n",file=file)
    return sheets

def Genera_Much_Description(sheets_name, serial=10, create=40, folder='.', filename='description', usage=1, seed=42):
    usages = []
    for sheet in sheets_name:
        usages.append('''use {} from "{}-*";'''.format(usage,sheet))
    usages = "\n".join(usages)
    d = """
directory ".";
seed {};
serial {};
{}
create {};""".format(seed,serial,usages,create)
    with open(os.path.join(folder,filename), 'w') as file:
        print(d, file=file)
    return


# ## Valutazione e reporting

def Valutazione(filename='elaborati.xlsx', p_cor=100, p_non=25, p_err=0):
    
    df = pd.read_excel(filename)
    
    punteggi = []
    report = {}

    for row in df.iterrows():
        punti = 0
        row = row[1]
        row = list(row)
        #idx = row.index.to_list()
        risposte = row[-2]
        if not isinstance(risposte, str):
            punteggi.append('')
            continue
        modello = row[2]
        domande = row[3:-3]
        studente = row[-1]
        corrette = row[-3]
        for c,r,d in zip(corrette,risposte,domande):
            d=d[:-2]
            if d not in report:
                report[d]={'corrette':0,'non date':0,'errate':0}
            if r=='-':
                punti+=p_non
                report[d]['non date']+=1
                continue
            if c==r:
                punti+=p_cor
                report[d]['corrette']+=1
                continue
            if c!=r:
                punti+=p_err
                report[d]['errate']+=1
        punteggi.append(punti)
        
    df['PUNTEGGI'] = punteggi

    df.to_excel(filename[:-4]+'_corretti.xlsx')
           
    return report

def Grafico_risposte(report, filename='valutazioni'):

    correct = []
    missing = []
    incorrect = []

    quest = report.keys()

    for q in quest:
        correct.append(report[q]['corrette'])
        missing.append(report[q]['non date'])
        incorrect.append(report[q]['errate'])

    correctmiss = [c+m for c,m in zip(correct,missing)]

    fig, ax = plt.subplots()

    fig.set_figheight(10)
    fig.set_figwidth(15)

    ax.bar(quest, correct, 0.2,  label='corrette', color='tab:blue')
    ax.bar(quest, missing, 0.2, bottom=correct,  label='non date', color='tab:gray')
    ax.bar(quest, incorrect, 0.2, bottom=correctmiss,  label='errate', color='tab:olive')

    ax.set_ylabel('Valore assoluto')
    ax.set_xlabel('Domande')
    ax.set_title('Report by question')
    ax.legend()

    plt.savefig(filename+'_analisi_risposte.png')
    
    return

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    
    parser.add_argument('-a', '--azione', help='[c]rea o [v]aluta un test', required=True, default='c', choices = ['c', 'v'])
    parser.add_argument('-f', '--filename', help='Nome del file contenente il test', required=False, default='questionario.xlsx')
    parser.add_argument('-n', '--numero', help='Numero di test da creare', required=False, default=30)
    parser.add_argument('-c', '--corrette', help='Punti per risposta corretta', required=False, default=4)
    parser.add_argument('-m', '--missing', help='Punti per risposta non data', required=False, default=1)
    parser.add_argument('-i', '--incorrette', help='Punti per risposta errata', required=False, default=0)  
    parser.add_argument('-v', '--valutazione', help='Nome del file contenente i test da valutare', required=False, default='elaborati.xlsx')
    parser.add_argument('-s', '--seed', help='Seme per la randomizzazione', required=False, default=42)  

    args = parser.parse_args()
    
    
    if args.azione=='c':

        # # Avvio creazione dei file PDF e di supporto alla valutazione

        try:
            os.mkdir('tmp')
        except:
            pass


        Genera_Tex(folder='tmp')

        sheets = Genera_file_domande(folder='tmp', filename=args.filename)

        Genera_Much_Description(sheets, folder='tmp', serial=10, create=args.numero, usage=1, seed=args.seed)
        
        #sleep(2)

        command = '''cd tmp && echo "c
{}" | much'''
        os.system(command.format('description'))

        for ext in ['jpg','gif','png','jpeg']:
            try:
                mover =  '''cp -f *.{} tmp'''.format(ext)
                os.system(mover)
            except:
                pass

        pdflatex = 'cd tmp && pdflatex exam.tex > /dev/null'
        os.system(pdflatex)

        os.system('cp -f {} exam.pdf'.format(os.path.join('tmp','exam.pdf')))
        os.system('cp -f {} exam.tex'.format(os.path.join('tmp','exam.tex')))

        pd.read_csv('tmp/mc-serials.txt', sep=' ', skiprows=1, header=None).to_excel('elaborati.xlsx')

        if True: ## cambiare
            try:
               # shutil.rmtree('tmp')
               pass
            except:
                pass


    if args.azione=='v':
        
        # # Avvio valutazione e creazione dei report

        report = Valutazione(filename=args.valutazione, p_cor=args.corrette, p_non=args.missing, p_err=args.incorrette)

        Grafico_risposte(report)




