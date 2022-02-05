#!/usr/bin/env python
from setuptools import setup

from rdfalchemy import __version__
install_requires = [
    'rdflib>=6.1.0',
    'SPARQLWrapper>=1.8.5',
    'wheel>=0.37.1',
    'lxml >= 4.7.1',
]

setup_requires = [
    'setuptools~=57.0.0'
]


setup(
    name='RDFAlchemy',
    version=__version__,
    description="rdflib wrapper",
    author='Philip Cooper',
    author_email='philip.cooper@openvest.com',
    maintainer='Graham Higgins',
    maintainer_email='gjh@bel-epa.com',
    url="http://www.openvest.com/trac/wiki/RDFAlchemy",
    download_url="https://github.com/gjhiggins/RDFAlchemy-%s.tar.gz" % (
        __version__),
    install_requires=install_requires,
    packages=['rdfalchemy',
              'rdfalchemy/engine',
              'rdfalchemy/samples',
              'rdfalchemy/sparql',
              ],
    include_package_data=True,
    keywords="RDF SPARQL",
    entry_points={
        'console_scripts': [
            'sparql = rdfalchemy.sparql.script:main',
        ],
    },
    platforms=["any"],
    classifiers=[
        "Programming Language :: Python",
        "License :: OSI Approved :: BSD License",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Operating System :: OS Independent",
        "Natural Language :: English",
    ],
    long_description="""RDFAlchemy is an abstraction layer that allowS Python
developers to use familiar *dot notation* to access and update an RDF
triplestore.

    * RDFAlchemy is an **ORM** (Object Rdf Mapper) for graph data as:
    * SQLAlchemy is an **ORM** (Object Relational Mapper) for relational
    databases

Allows access to:

      * rdflib_ datastores
      * Sesame_ Repositories
      * SPARQL_ endpoints

Provides intuitive access to RDF values by accessing predicate values
through dot notation. ::


    ov = Namespace('http://owl.openvest.org/2005/10/Portfolio#')

    class Company(rdfSubject):
        rdf_type = ov.Company
        symbol = rdfSingle(ov.symbol,'symbol')  #second param is optional
        cik = rdfSingle(ov.secCik)
        companyName = rdfSingle(ov.companyName)

    c = Company.query.get_by(symbol = 'IBM')
    print("%s has an SEC symbol of %s" % (c.companyName, c.cik))

Includes advanced descriptors for read/write access to lists and collections.

.. _rdflib: https://github.com/RDFLib/rdflib
.. _Sesame: http://www.openrdf.org
.. _SPARQL: http://www.w3.org/TR/rdf-sparql-query/
    """,
    setup_requires=setup_requires
)
