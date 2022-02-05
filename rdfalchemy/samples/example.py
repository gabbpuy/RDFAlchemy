import logging
import os

from rdflib import ConjunctiveGraph, Namespace
from rdfalchemy import rdfSingle
from rdfalchemy.rdf_subject import rdfSubject
from rdfalchemy.namespaces import OV, VCARD

log = logging.getLogger()

non_core = True

rdfSubject.db = ConjunctiveGraph()
rdfSubject.db.load(
    os.path.join(os.path.split(__file__)[:-1])[0] + '/data/example.n3',
    format='n3')


class Company(rdfSubject):
    rdf_type = OV.Company
    symbol = rdfSingle(OV.symbol, 'symbol')
    cik = rdfSingle(OV.secCik, 'cik')
    companyName = rdfSingle(OV.companyName)
    address = rdfSingle(VCARD.adr)


# Above here would typically go in a model.py file and be imported
##########################################################################
# Below here goes in the file with business logic agnostic of persistance

c = Company.get_by(symbol='IBM')
## this will enable us to see that the reads are cached

log = logging.getLogger('rdfAlchemy')
## comment out to quiet debug messages
log.setLevel(logging.DEBUG)

## items Companies
for c in Company.ClassInstances():
    print("%s has an SEC symbol of %s" % (c.companyName, c.cik))
print('')

c = Company.get_by(symbol='IBM')

## Add a descriptor on the fly
Company.stockDescription = rdfSingle(OV.stockDescription, 'stockDescription')

print("%s: %s" % (c.companyName, c.stockDescription))
print(" same as")
print("%s: %s" % (c[OV.companyName], c[OV.stockDescription]))

print("## CHECK to see if multiple reads cause database reads")
print("   you should see no non-blank lines between here\n")
s = "%s: %s" % (c.companyName, c.stockDescription)
s = "%s: %s" % (c.companyName, c.stockDescription)
print("\n   and here")

c = Company.get_by(symbol='IBM')
print("   and exactly the same number of non-blank lines between here\n")
s = "%s: %s" % (c.companyName, c.stockDescription)
print("\n   and here")

c = Company.get_by(symbol='IBM')
print("   and  here\n")
s = "%s: %s" % (c.companyName, c.stockDescription)
s = "%s: %s" % (c.companyName, c.stockDescription)
s = "%s: %s" % (c.companyName, c.stockDescription)
print("\n   and here")

## add another descriptor on the fly
Company.industry = rdfSingle(OV.yindustry, 'industry')

## add an attribute (from the database)
c = Company.get_by(symbol='JAVA')
c.industry = 'Computer stuff'

## delete an attribute (from the database)
c = Company.get_by(symbol='IBM')
del c.industry

# write out the new n3 file to see the changes
c.db.serialize('example-out.n3', format='n3')
