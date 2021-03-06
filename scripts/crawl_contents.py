#! /usr/bin/env python
# -*- coding: utf-8 -*-
from lxml import html
import requests
import re
import os
import sys
import json
import codecs
import create_sphinx_tables

class Anpr(object):
    @staticmethod
    def domain():
        return "https://www.anpr.interno.it"


class Table(object):
    def __init__(self,id, url, source="", title="", date="", note=""):
        self.id = id
        self.url = url
        self.source = source
        self.title = title
        self.date = date
        self.note = note
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


def scrapeHtml(xlsxpath,rstpath,url,section_prefix):
    page = requests.get(Anpr.domain()+url)
    print ("Get all Excel files from " +Anpr.domain()+url)
    tree = html.fromstring(page.content)

    xpath_expr = "//tr[td//a[contains(@href,'.xlsx')]]"
    #xpath_expr = "//table[tr[td//a[contains(@href,'.xlsx')]]]"

    allTrWithTh = tree.xpath(xpath_expr)
    files_array =[]

    for tr in allTrWithTh:
        tds = tr.getchildren()
        href_url = tds[1].getchildren()[0].get("href")
        xls_url = href_url
        if((Anpr.domain() not in href_url) and ("portale/documents/" in href_url) ):
            xls_url = Anpr.domain()+ href_url

        title = tds[1].getchildren()[0].text

        files_array.append(Table(tds[0].text,xls_url,tds[2].text,title,tds[3].text,tds[4].text))

    toclist = []
    for data in files_array:
        if data.title is None:
            print "FIXME: data.title is None in file:", data.url
            continue
        tocitem = createRstFromXlsx(data)
        #print tocitem, data.url
        if tocitem is not None:
            toclist.append(tocitem)

    return toclist


def createRstFromXlsx(data, table=True, startFromRow=0, endRow=2000, nCols=2, headers=[], legend=""):
    xlsx_name, rst_name = wGetAndRename(xlsxpath,rstpath,data.url,data.title,"tab")
    if xlsx_name == "":
        return

    f = codecs.open(rst_name, "w", "utf-8")
    tablename = "%s" % (data.title)
    if table:
        tablename = "Tabella %s - %s" % (data.id, data.title)

    print >>f, tablename
    print >>f, "="*len(tablename)
    print >>f
    if data.date.strip():
        print >>f, ":Aggiornamento: %s" % data.date
    if data.source.strip():
        print >>f, ":Fonte: %s" % data.source
    if data.note.strip():
        print >>f, ":Note: %s" % data.note

    if legend:
        print >>f
        print >>f, ".. note:: %s" %legend
    print >>f
    print >>f, "`Download <%s>`_" % data.url
    print >>f
    print os.path.getsize(xlsx_name);
    if (os.path.getsize(xlsx_name)<1000000):
        create_sphinx_tables.convertXlsxToRst(xlsx_name, f, startFromRow,endRow,nCols,headers)
    f.close()
    print data.id,tablename
    return (int(data.id),os.path.splitext(os.path.basename(rst_name))[0])



def createtoc(rstpath, toclist):
    # generate toc
    f = open(rstpath + "/toc_tabelle_riferimento.rst", "w")


    print >>f, ".. include:: index.rst"
    print >>f,""
    print >>f, ".. toctree::"
    print >>f, "    :maxdepth: 3"
    print >>f, "    :caption: Contenuti"
    print >>f
    print toclist
    toclist = filter(None, toclist)
    toclist.sort(key=lambda x: x[0], reverse=False)

    for id,name in toclist:
        print >>f, "    %s" % name
    f.close()


def wGetAndRename(xlsxpath,rstpath,url,title,section_prefix):
    print "File to download " +url
    try:
        r = requests.get(url ,stream=True,allow_redirects=True, headers = {'User-agent': 'Mozilla/5.0'})
        r.raise_for_status()
    except requests.ConnectionError:
        print "ERROR: downloading file, skipping"
        return "", ""


    file_content = r.raw.read()
    #print file_content
    print "Downloading: [" + url+ "]"
    print "Title:", title
    base_name = section_prefix+"_"+ re.sub(r'([^.a-zA-Z0-9_])','_',title)
    base_name = base_name.lower()

    xlsx_name = xlsxpath + "/" + base_name + ".xlsx"
    if(url.endswith('.xls')):
        xlsx_name = xlsxpath + "/" + base_name + ".xls"

    rst_name = rstpath + "/" + base_name + ".rst"

    with open(xlsx_name, 'w') as f:
        f.write(file_content)

    if(url.endswith('.xls')):
        print "convert table"
        xlsx_name =create_sphinx_tables.convert_xls_to_xlsx(xlsx_name, xlsxpath + "/" + base_name + ".xlsx")

    return xlsx_name, rst_name



if __name__ == "__main__":
    if len(sys.argv) < 3:
        print "use get_tabelle.py [xlsx-path] [rst-path]"
        sys.exit(2)

    xlsxpath = sys.argv[1]
    rstpath = sys.argv[2]
    toclist = []

    toclist = scrapeHtml(xlsxpath, rstpath, "/portale/tabelle-di-riferimento","tab")

    toclist.append(createRstFromXlsx(Table(
        id=-5, url=Anpr.domain()+"/portale/documents/20182/26001/aggiornamenti_12_07_2017.xlsx/5032d741-f001-4dea-b653-15ee7999b5cb",
        title="Aggiornamenti alla documentazione tecnica", date="12 Luglio 2017",
    ),False,0,2000,4))


    toclist.append(createRstFromXlsx(Table(
        id=-4, url=Anpr.domain()+"/portale/documents/20182/26001/Allegato_5_Elenco_WS_di_ANPR_12072017.xlsx/01e57b03-5ac4-407c-8cee-f50e61b6e0d6",
        title="Elenco dei web services da utilizzare per aggiornamento delle basi dati locali", date="12 Luglio 2017",
    ),False,4,9,4, ['Servizio', 'Op. Anagrafica','Descrizione', u'Servizio Esposto','Note','',''],u"Il comune che non espone il servizio per acquisizione delle notifiche effettua una richiesta utilizzando il servizio 3003 o 3007, specificando il tipo di notifica da consultare."))

    toclist.append(createRstFromXlsx(Table(
        id=-4, url=Anpr.domain()+"portale/documents/20182/26001/Utilizzo+WS+ANPR+27072016.xlsx",
        title="Utilizzo del WebService", date="12 Luglio 2017",
    ),False,4,37,3, ['Servizio', 'Op. Anagrafica','Descrizione', u'WS da Utilizzare - modalità ws', u'WS da Utilizzare - modalità wa',u'Notifiche - modalità ws',u'Notifiche - modalità wa','Note',"- ","- "]))

    toclist.append(createRstFromXlsx(Table(
        id=-3, url=Anpr.domain()+"/portale/documents/20182/26001/Allegato+5+-+Elenco+WS+di+ANPR+13102016.xlsx/a787b18d-a271-482c-bbb4-c3559d2b93c0",
        title="Elenco dei web services disponibili", date="17 dicembre 2017",
    ),False,0,2000,5))

    toclist.append(createRstFromXlsx(Table(
        id=-2, url=Anpr.domain()+"/portale/documents/20182/26001/Allegato+2+-+Elenco+funzioni+WEB2772016.xlsx",
        title="Elenco delle funzionalita' disponibilini nella web app", date="17 Marzo 2017",
    ),False,0,2000,3))

    errori_path="https://www.anpr.interno.it/portale/documents/20182/26001/errori_anpr+31082017_bis.xlsx/5699b8aa-7ba3-411b-91bf-6013ac1e6dab"

    toclist.append(createRstFromXlsx(Table(
        id=-1, url=errori_path, title="Elenco Errori ANPR", date="31 Agosto 2017",
    ),False,3,2000,4, [ 'Codice', 'Descrizione', "Tabella Di Riferimento", u'Subentro - Severità', "Note", u"Servizi- Severità" ,"Servizi: Note" , "Data Ultima variazione"], "Il simbolo @ viene sostituito dal valore del campo errato/anomalo. W - Anomalia, E- Errore Bloccante."))


    toclist.append(createRstFromXlsx(Table(
        id=0, url=Anpr.domain()+"/portale/documents/20182/26001/errori_ae_11_05_2017.xlsx/eb45d775-21f1-4436-9a86-b8ab0169aee6",
        title="Errori Agenzia Entrate", date="12 Maggio 2017",
    ),False,nCols=3))

    toclist.append(createRstFromXlsx(Table(
        id=4, url=Anpr.domain()+"/portale/documents/20182/50186/Tabella_4.xlsx/128b4cc9-2017-4859-a0ae-7b5be7584c39",
        title="Tabella 04 - Specie Toponimo", source="Agenzia delle Entrate"
    ),False))


    toclist.append(createRstFromXlsx(Table(
        id=41, url="http://servizidemografici.interno.it/sites/default/files/T_Assoc-StatoTerritConsolato_20160531_0.xls",
        title="Tabella 41 - Stati Territori Consolati", source="Servizi demografici del Ministero dell'Interno", date="17 Giugno 2016"
    ),False,2,2000,7,['Codice Stato/Territorio', 'Denominazione Stato/Territorio', 'Codice Consolato', 'Rango', 'Sede', 'Codice Stato di appartenenza', 'Denominazione stato di appartenenza']))


    toclist.append(createRstFromXlsx(Table(
        id=40, url="http://servizidemografici.interno.it/sites/default/files/T_Elenco-Consolati_20160531_1.xls",
        title="Tabella 40 - Elenco dei consolati", source="Servizi demografici del Ministero dell'Interno", date="17 Giugno 2016"
    ),False,nCols=4,startFromRow=1))

    createtoc("../src/tab", toclist)
