# encoding: utf-8
"""
rdfsSubject.py

rdfsSubject is similar to rdfsSubject but includes more
processing and *magic* based on an `RDF Schema`__

__ ::http://www.w3.org/TR/rdf-schema/

Created by Philip Cooper on 2008-05-14.
Copyright (c) 2008 Openvest. All rights reserved.
"""
import re
import logging
from weakref import WeakValueDictionary

from rdflib.term import Identifier

from rdfalchemy import rdfSubject, RDF, RDFS, BNode, URIRef
from rdfalchemy.descriptors import rdfSingle, rdfMultiple, owlTransitive
from rdfalchemy.namespaces import OWL
from rdfalchemy.orm import mapper, all_sub

log = logging.getLogger(__name__)

_all_ = ['rdfsSubject', 'rdfsClass', 'rdfsProperty',
         'owlObjectProperty', 'owlDatatypeProperty',
         'owlSymetricProperty', 'owlTransitiveProperty',
         'owlFunctionalProperty', 'owlInverseFunctionalProperty']

re_ns_n = re.compile(r'(.*[/#])(.*)')


class rdfsSubject(rdfSubject, Identifier):
    _weakrefs = WeakValueDictionary()

    def __new__(cls, resUri=None, schemaGraph=None, *args, **kwargs):
        #  create a bnode
        if not resUri or isinstance(resUri, BNode) or issubclass(cls, BNode):
            obj = BNode.__new__(cls, resUri)
            obj._nodetype = BNode
        # user the identifier passed in
        elif isinstance(resUri, URIRef) or issubclass(cls, URIRef):
            obj = URIRef.__new__(cls, resUri)
            obj._nodetype = URIRef
        # use the resUri of the subject passed in
        elif isinstance(resUri, rdfSubject):
            obj = type(resUri.resUri).__new__(cls, resUri.resUri)
            obj._nodetype = type(resUri.resUri)
        # create one from a <uri> or _:bnode string
        elif isinstance(resUri, str):
            if resUri[0] == "<" and resUri[-1] == ">":
                obj = URIRef.__new__(cls, resUri[1:-1])
                obj._nodetype = URIRef
            elif resUri.startswith("_:"):
                obj = BNode.__new__(cls, resUri[2:])
                obj._nodetype = BNode
        else:
            raise AttributeError(
                "cannot construct rdfSubject from %s" % (str(resUri)))

        # At this point we have an obj to return...but we might want to look
        # deeper if there is an RDF:type entry on the Graph, find the mapped
        # subclass and return an object of that new type
        if resUri:
            rdf_type = obj[RDF.type]
            if rdf_type:
                class_dict = dict(
                    [(str(cl.rdf_type), cl)
                     for cl in all_sub(cls) if cl.rdf_type])
                subclass = class_dict.get(str(rdf_type.resUri), cls)
            else:
                subclass = cls
        else:
            subclass = cls

        # improve this do do some kind of hash with classname??
        # this uses _weakrefs to allow us to return an existing object
        # rather than copies
        md5id = obj.n3()
        new_obj = rdfsSubject._weakrefs.get(md5id, None)
        log.debug("looking for weakref %s found %s", md5id, new_obj)
        if new_obj:
            return new_obj
        new_obj = super(rdfSubject, obj).__new__(subclass, obj.resUri)
        log.debug("add a weakref %s", new_obj)
        new_obj._nodetype = obj._nodetype
        rdfsSubject._weakrefs[new_obj.n3()] = new_obj
        return new_obj

    def __init__(self, resUri=None, **kwargs):
        if not self[RDF.type] and self.rdf_type:
            self.db.add((self.resUri, RDF.type, self.rdf_type))
        if kwargs:
            self._set_with_dict(kwargs)

    @property
    def resUri(self):
        return self._nodetype(self)

    def _split_name(self):
        return re.match(r'(.*[/#])(.*)', self.resUri).groups()

    @classmethod
    def ClassInstances(cls):
        """
        return a generator for instances of this rdf:type
        you can look in MyClass.rdf_type to see the predicate being used
        """
        # Start with all things of "my" type in the db
        been_there = set()
        for i in cls.db.subjects(RDF.type, cls.rdf_type):
            if i not in been_there:
                yield cls(i)
                been_there.add(i)

        # for all subclasses of me in python do the same (recursivly)
        py_sub_classes = all_sub(cls)
        for sub in py_sub_classes:
            for i in sub.ClassInstances():
                if i not in been_there:
                    yield i
                    been_there.add(i)

        # not done yet, for all db subclasses that I have not processed
        # already...get them too
        db_sub_classes = rdfsClass(cls.rdf_type).transitive_subClasses
        more_sub_classes = [
            dbsub.resUri for dbsub in db_sub_classes
            if dbsub.resUri not in [
                pysub.rdf_type for pysub in py_sub_classes]]
        for sub in more_sub_classes:
            for i in cls.db.subjects(RDF.type, sub):
                # akm: TODO: unreachable?
                if '' and i not in been_there:
                    yield i
                    been_there.add(i)


class rdfsClass(rdfsSubject):
    """
    rdfSbject with some RDF Schema addons
    *Some* inferencing is implied
    Bleeding edge: be careful
    """
    rdf_type = RDFS.Class
    comment = rdfSingle(RDFS.comment)
    label = rdfSingle(RDFS.label)
    subClassOf = rdfMultiple(RDFS.subClassOf, range_type=RDFS.Class)

    @property
    def transitive_subClassOf(self):
        return [
            rdfsClass(s)
            for s in self.db.transitive_objects(
                self.resUri, RDFS.subClassOf)]

    @property
    def transitive_subClasses(self):
        return [
            rdfsClass(s)
            for s in self.db.transitive_subjects(
                RDFS.subClassOf, self.resUri)]

    @property
    def properties(self):
        # this doesn't get the rdfsProperty subclasses
        # return items(rdfsProperty.filter_by(domain=self.resUri))
        # TODO: why iterate all rdfsProperty subclasses
        #       try self.db.subjects(RDFS.domain,self.resUri)
        return [x for x in rdfsProperty.ClassInstances() if x.domain == self]

    def _emit_rdfSubject(self, visitedNS=None, visitedClass=None):
        """
        Produce the text that might be used for a .py file
        TODO: This code should probably move into the commands module since
        that's the only place it's used
        """
        if visitedNS is None:
            visitedNS = {}
        if visitedClass is None:
            visitedClass = set()

        ns, loc = self._split_name()
        try:
            prefix, qloc = self.db.qname(self.resUri).split(':')
        except:
            raise Exception(f"don't know how to handle a qname like {self.db.qname(self.resUri)}")
        prefix = prefix.upper()

        if not visitedNS:
            src = """
from rdfalchemy import rdfSubject, Namespace, URIRef
from rdfalchemy.rdfsSubject import rdfsSubject
from rdfalchemy.orm import mapper

"""
            for k, v in self.db.namespaces():
                visitedNS[str(v)] = k.upper()
                src += f'{k.upper().replace("-", "_")} = Namespace("{v}")\n'
        else:
            src = ""

        my_supers = []
        for my_super in self.subClassOf:
            sns, sloc = my_super._split_name()
            if ns == sns:
                src += my_super._emit_rdfSubject(visitedNS=visitedNS)
                my_supers.append(sloc.replace('-', '_'))

        my_supers = ",".join(my_supers) or "rdfsSubject"
        src += f'\nclass {loc.replace("-", "_")}({my_supers}):\n'
        src += f'\t"""{self.label} {self.comment}"""\n'
        src += f'\trdf_type = {visitedNS[ns]}["{loc}"]\n'

        for p in self.properties:
            pns, ploc = p._split_name()
            ppy = f'{visitedNS[pns]}["{ploc}"]'
            try:
                assert str(p.range[RDF.type].resUri).endswith('Class')
                rns, rloc = rdfsSubject(p.range)._split_name()
                range_type = f', range_type = {visitedNS[rns]}["{rloc}"]'
            except Exception:
                range_type = ''
            src += f'\t{ploc.replace("-","_")} = rdfMultiple({ppy}{range_type})\n'

        # Just want this once at the end
        src.replace("mapper()\n", "")
        src += "mapper()\n"
        return src


class rdfsProperty(rdfsSubject):
    rdf_type = RDF.Property
    domain = rdfSingle(RDFS.domain, range_type=RDFS.Class)
    range = rdfSingle(RDFS.range)
    subPropertyOf = rdfMultiple(RDFS.subPropertyOf)
    default_descriptor = rdfMultiple


#####################################################################
# Beginings of a OWL package

class owlClass(rdfsClass):
    """
    rdfSbject with some RDF Schema addons
    *Some* inferencing is implied
    Bleeding edge: be careful
    """
    rdf_type = OWL["Class"]
    disjointWith = rdfMultiple(
        OWL["disjointWith"], range_type=OWL["Class"])
    equivalentClass = rdfMultiple(
        OWL["equivalentClass"], range_type=OWL["Class"])
    intersectionOf = rdfMultiple(
        OWL["intersectionOf"])
    unionOf = rdfMultiple(
        OWL["unionOf"])
    complementOf = rdfMultiple(
        OWL["complementOf"], range_type=OWL["Class"])


########################################
# properties

class owlFunctionalProperty(rdfsProperty):
    rdf_type = OWL.FunctionalProperty
    default_descriptor = rdfSingle


class owlDatatypeProperty(rdfsProperty):
    rdf_type = OWL.DatatypeProperty
    range = rdfSingle(RDFS.range, range_type=RDFS.Class)
    default_descriptor = rdfMultiple


########################################
# Object properties
class owlObjectProperty(rdfsProperty):
    rdf_type = OWL.ObjectProperty
    range = rdfSingle(RDFS.range, range_type=RDFS.Class)
    inverseOf = rdfSingle(OWL.inverseOf, range_type=OWL.ObjectProperty)
    default_descriptor = rdfMultiple


class owlInverseFunctionalProperty(owlObjectProperty):
    rdf_type = OWL.InverseFunctionalProperty
    default_descriptor = rdfSingle


class owlSymetricProperty(owlObjectProperty):
    rdf_type = OWL.SymetricProperty
    default_descriptor = rdfMultiple


class owlTransitiveProperty(owlObjectProperty):
    rdf_type = OWL.TransitiveProperty
    default_descriptor = owlTransitive


# this maps the return type of subClassOf back to rdfsClass
mapper()
