from itertools import islice
import logging

from rdflib import Namespace, Graph, URIRef, RDFS, RDF
from rdflib.plugins.stores.sparqlstore import SPARQLStore

from rdfalchemy import rdfMultiple
from rdfalchemy.descriptors import rdfAbstract, rdfLocale
from rdfalchemy.namespaces import DBPO, DC, FOAF, UMBEL
from rdfalchemy.orm import mapper
from rdfalchemy.rdf_subject import rdfSubject

log = logging.getLogger('rdfalchemy.rdfSubject')
log.setLevel(logging.WARN)

# Main graph on which RDFAlchemy will operate
main_graph = Graph()
# Plug the ORM on the loaded graph
rdfSubject.db = main_graph


# Define RDFAlchemy descriptors
class Film(rdfSubject):
    """DBPedia films"""
    rdf_type = DBPO.Film
    # title = rdfMultiple(RDFS.label)
    title = rdfLocale(RDFS.label, 'en')
    frtitle = rdfLocale(RDFS.label, 'fr')
    subject = rdfMultiple(DC.subject)
    actor = rdfMultiple(DBPO.starring, range_type=UMBEL.Actor)


class Actor(rdfSubject):
    """DBPedia actors"""
    rdf_type = UMBEL.Actor
    # name = rdfMultiple(FOAF.name)
    name = rdfLocale(FOAF.name, 'en')
    frname = rdfLocale(FOAF.name, 'fr')


# bind film's actors
mapper(Film, Actor)


# Utility function which lists predicates of a descriptor class
def predicates_of_descriptor(cls):
    predicates = []
    types = []
    for f in cls.__dict__:
        p = cls.__dict__[f]
        t = None
        mapped = None
        if issubclass(type(p), rdfAbstract):
            t = p.pred
            mapped = getattr(p, '_mappedClass', None)
        elif f == 'rdf_type':
            t = RDF.type
        if t and t not in types:
            types.append(t)
            predicates.append({'predicate': t, 'mapped': mapped})
    return predicates


# Utility function which populates a target graph with values of all
# attributes for a descriptor class
# Avoids loading tons of details if we want just a partial view
# It iterates over mapped attributes
def populate_predicate_objects(destgraph, srcgraph, cls, subject):
    predicates = predicates_of_descriptor(cls)
    for predicate in predicates:
        p = predicate['predicate']
        m = predicate['mapped']
        for o in srcgraph.objects(subject, p):
            destgraph.add((subject, p, o))
            if m:
                populate_predicate_objects(destgraph, srcgraph, m, o)


if __name__ == '__main__':

    # Allows to debug SPARQLWrapper queries to remote endpoint
    if 0:
        handler = urllib2.HTTPHandler(debuglevel=1)
        opener = urllib2.build_opener(handler)
        urllib2.install_opener(opener)

    # Declare a remote RDFLib SPARQL Store
    store = SPARQLStore("https://dbpedia.org/sparql", context_aware=False)

    # Plug 
    graph = Graph(store)

    # Load french films in DBPedia
    subject = DC.subject
    french_film = URIRef("https://dbpedia.org/resource/Category:French_films")

    # load every details we're interested in to the main_graph in memory
    # (actually, only the 50 first films)
    print("Select subjects for french films with SPARQLStore -> SPARQWrapper:")
    print("------------------------------------------------------------------")
    # for film in graph.subjects(subject, french_film):
    for film in islice(graph.subjects(subject, french_film), 50):
        print(film)

        # We don't load every details with
        #     for p, o in graph.predicate_objects(film):
        #         #print type(film), type(p), type(o)
        #         main_graph.add( (film, p, o) )

        # And instead use :
        populate_predicate_objects(main_graph, graph, Film, film)

    # Allows to debug RDFAlchemy
    if 0:
        log = logging.getLogger('rdfalchemy.rdfSubject')
        log.setLevel(logging.DEBUG)

    print()
    print("Actors in french films :")
    print("------------------------")
    # We limit the number of elements processed
    # for f in Film.filter_by(subject = french_film):
    for f in islice(Film.filter_by(subject=french_film), 10):
        print("*", f.title.encode("utf-8"), '/', f.frtitle.encode("utf-8"), "*")
        for a in f.actor:
            print('starring', end='')
            if not a.name:
                print(a)
            else:
                print(a.name.encode("utf-8"), '/', a.frname.encode("utf-8"))
        print()

    print()
    print("Films starring Michel Piccoli :")
    print("-------------------------------")
    for f in Film.filter_by(subject=french_film, actor=URIRef('http://dbpedia.org/resource/Michel_Piccoli')):
        print('-', f.title.encode("utf-8"), '/', f.frtitle.encode("utf-8"))
