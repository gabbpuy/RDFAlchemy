from rdflib import Namespace
# this has the rdfSubject stuff and the Fresnel stuff
from rdfalchemy import rdfSingle, rdfMultiple
from rdfalchemy.rdf_subject import rdfSubject
from rdfalchemy.namespaces import OV
non_core = True

edgarns = Namespace('http://www.sec.gov/Archives/edgar')


class Company(rdfSubject):
    rdf_type = OV.Company
    symbol = rdfSingle(OV.symbol, )
    cik = rdfSingle(OV.secCik, 'cik')
    companyName = rdfSingle(OV.companyName, 'companyName')
    stockDescription = rdfSingle(OV.stockDescription, 'stockDescription')
    stock = rdfMultiple(OV.hasIssue)


class EdgarFiling(rdfSubject):
    rdf_type = edgarns.xbrlFiling
    accessionNumber = rdfSingle(edgarns.accessionNumber)
    companyName = rdfSingle(edgarns.companyName)
    filingDate = rdfSingle(edgarns.filingDate)
    formType = rdfSingle(edgarns.formType)
