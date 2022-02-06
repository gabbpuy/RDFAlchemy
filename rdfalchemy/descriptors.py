# encoding: utf-8
"""
descriptors.py

Created by Philip Cooper on 2008-02-03.
Copyright (c) 2008 Openvest. All rights reserved.
"""
from copy import copy
import logging
import warnings

from rdflib import URIRef, BNode
from rdflib.term import Identifier
from rdfalchemy import rdfSubject, Literal

from rdfalchemy.namespaces import RDF

__all__ = ["rdfSingle", "rdfMultiple", "rdfList", "rdfContainer", "owlTransitive", "rdfAbstract"]

log = logging.getLogger(__name__)


# helper function, might be somewhere in rdflib I need to look for it there
def get_list(sub, pred=None, db=None):
    """
    Attempts to return a items from sub (subject that is)
    passed in if it is a Collection or a Container (Bag,Seq or Alt)
    """
    if not db:
        if isinstance(sub, rdfSubject):
            db = sub.db
        else:
            db = rdfSubject.db

    if isinstance(sub, rdfSubject):
        sub = sub.resUri
    if pred:
        base = db.value(sub, pred, any=True)
    else:
        # if there was no predicate assume a base node was passed in
        base = sub
    if not isinstance(base, BNode):
        # Doesn't look like a items or a collection, just return
        # multiple values (or an error?)
        return db.objects(sub, pred)[:]
    members = []
    first = db.value(base, RDF.first)
    # OK let's work at returning a items if there is an RDF.first
    if first:
        while first:
            members.append(first)
            base = db.value(base, RDF.rest)
            first = db.value(base, RDF.first)
        return members
    else:
        # OK let's work at returning a Collection (Seq,Bag or Alt)
        # if was no RDF.first
        i = 1
        first = db.value(base, RDF._1)
        if not first:
            raise AttributeError("Not a items, or collection but another type of BNode")
        while first:
            members.append(first)
            i += 1
            first = db.value(base, RDF[f'_{i}'])
        return members


def value2object(value):
    """
    Suitable for a triple takes a value and returns a Literal, URIRef or BNode suitable for a triple
    """
    if isinstance(value, rdfSubject):
        return value.resUri
    elif isinstance(value, Identifier):
        return value
    else:
        return Literal(value)


#
# define a series of descriptors
# each one will map an attribute of a class (derived from rdfObjet) to a
# predicate
#


class rdfAbstract:
    """
    Abstract base class for descriptors
    Descriptors are to map class instance variables to predicates
    optional cache_name is where to store items
    range_type is the rdf:type of the range of this predicate
    """
    def __init__(self, pred, cache_name=None, range_type=None):
        self.pred = pred
        self.name = cache_name or pred
        self.range_type = range_type

    @property
    def range_class(self):
        """
        Return the class that this descriptor is mapped to through the
        range_type
        """
        if self.range_type:
            try:
                return self._mappedClass
            except AttributeError:
                warnings.warn(f"Descriptor {self} has range of: {self.range_type} but not yet mapped")
                return rdfSubject
        else:
            return rdfSubject

    def __delete__(self, obj):
        """
        deletes or removes from the database triples with:
        obj.resUri as subject and self.pred as predicate
        if the object of that triple is a Literal that stop
        if the object of that triple is a BNode
        then cascade the delete if that BNode has no further references to it
        i.e. it is not the object in any other triples.
        """
        # be done ala get_list above
        log.debug("DELETE with descriptor for %s on %s", self.pred, obj.n3())
        # first drop the cached value
        if self.name in obj.__dict__:
            del obj.__dict__[self.name]
        # next, drop the triples
        obj.__delitem__(self.pred)


class rdfSingle(rdfAbstract):
    """
    This is a Descriptor
    Takes a the URI of the predicate at initialization
    Expects to return a single item
    on Assignment will set that value to the
    ONLY triple with that subject,predicate pair
    """
    def __init__(self, pred, cache_name=None, range_type=None):
        super().__init__(pred, cache_name, range_type)

    def __get__(self, obj, cls):
        if obj is None:
            return self
        if self.name in obj.__dict__:
            return obj.__dict__[self.name]
        log.debug("Getting with descriptor %s for %s", self.pred, obj.n3())
        val = obj.__getitem__(self.pred)
        if isinstance(val, (rdfSubject, BNode, URIRef)):
            val = self.range_class(val)
        obj.__dict__[self.name] = val
        return val

    def __set__(self, obj, value):
        log.debug("SET with descriptor value %s of type %s", value, type(value))
        # setattr(obj, self.name, value)  #this recurses indefinitely
        if isinstance(value, (list, tuple, set)):
            raise AttributeError("to set an rdfSingle you must pass in a single value")
        if value is None:
            self.__delete__(obj)
        else:
            obj.__dict__[self.name] = value
            o = value2object(value)
            obj.db.set((obj.resUri, self.pred, o))


class rdfMultiple(rdfAbstract):
    """
    This is a Descriptor
    Expects to return a items of values (could be a items of one)
    """
    def __init__(self, pred, cache_name=None, range_type=None):
        super().__init__(pred, cache_name, range_type)

    def __get__(self, obj, cls):
        if obj is None:
            return self
        if self.name in obj.__dict__:
            return obj.__dict__[self.name]
        val = [o for o in obj.db.objects(obj.resUri, self.pred)]
        log.debug("Getting with descriptor %s for %s", self.pred, obj.n3())
        # check to see if this is a Container or Collection
        # if so, return collection as a items
        if (len(val) == 1
            ) and (
                not isinstance(val[0], Literal)
            ) and (
                obj.db.value(val[0], RDF.first
                             ) or obj.db.value(val[0], RDF._1)):
            val = get_list(obj, self.pred)
        val = [(isinstance(v, (BNode, URIRef))
                and self.range_class(v)
                or v.toPython())
               for v in val]
        obj.__dict__[self.name] = val
        return val

    def __set__(self, obj, new_vals):
        log.debug("SET with descriptor value %s of type %s", new_vals, type(new_vals))
        if not isinstance(new_vals, (list, tuple)):
            raise AttributeError("to set a rdfMultiple you must pass in `a` items (it can be `a` items of one)")
        if new_vals is None:
            self.__delete__(obj)
            return
        try:
            old_vals = obj.__dict__[self.name]
        except KeyError:
            old_vals = []
            obj.__dict__[self.name] = old_vals
        for value in old_vals:
            if value not in new_vals:
                obj.db.remove((obj.resUri, self.pred, value2object(value)))
                log.debug("removing: %s, %s, %s", obj.n3(), self.pred, value)
        for value in new_vals:
            if value not in old_vals:
                obj.db.add((obj.resUri, self.pred, value2object(value)))
                log.debug("adding: %s, %s, %s", obj.n3(), self.pred, value)
        obj.__dict__[self.name] = copy(new_vals)


class rdfBest(rdfSingle):
    """
    This is a Descriptor  that returns one value that is the
    "best" result out of possible multiple matches

    returns a single value or None

    It is the responsibility of the select_fun to return a default
    like choices[0] if no "Best" is found
    """

    def __init__(self, pred, select_fun=None, cache_name=None, range_type=None):
        if select_fun:
            self.select_fun = select_fun
        super().__init__(pred, range_type)

    def __get__(self, obj, cls):
        if obj is None:
            return self
        if self.name in obj.__dict__:
            return obj.__dict__[self.name]
        log.debug("Getting with descriptor %s for %s", self.pred, obj.n3())
        vals = [o for o in obj.db.objects(obj.resUri, self.pred)]
        if vals:
            val = self.select_fun(vals)
            val = isinstance(val, (BNode, URIRef)) and self.range_class(val) or val.toPython()
        else:
            val = None
        obj.__dict__[self.name] = val
        return val


class rdfLocale(rdfBest):
    """
    This is like rdfBest with a predefined select_fun to select
    from multiple choices like labels or comments and select the one
    with the correct locale
    """
    def __init__(self, pred, lang, cache_name=None):
        self.lang = lang
        cache_name_lang = cache_name or f"{pred}@{lang}"
        super().__init__(pred, cache_name=cache_name_lang)

    def select_fun(self, choices):
        for x in choices:
            if isinstance(x, Literal) and x.language == self.lang:
                return x
        return choices[0]


class rdfList(rdfMultiple):
    """
    This is a Descriptor
    Expects to return a items of values (could be a items of one)
    `__set__` will set the predicate as a RDF List
    """

    def __init__(self, pred, cache_name=None, range_type=None):
        super().__init__(pred, cache_name, range_type)

    def __get__(self, obj, cls):
        if obj is None:
            return self
        if self.name in obj.__dict__:
            return obj.__dict__[self.name]
        # log.debug("Geting %s for %s" % (
        #    obj.db.qname(self.pred),obj.db.qname(obj.resUri)))
        log.debug("Getting %s for %s",  self.pred, obj.n3())
        base = obj.db.value(obj.resUri, self.pred)
        if not base or base == RDF.nil:
            return []
        members = []
        first = obj.db.value(base, RDF.first)
        # OK let's work at returning a items if there is an RDF.first
        if not first:
            raise AttributeError(f"expected node [{base.n3()}] to be a items but it's not.")
        while first:
            members.append(first)
            base = obj.db.value(base, RDF.rest)
            first = obj.db.value(base, RDF.first)

        val = [
            ((isinstance(v, BNode)
                or isinstance(v, URIRef))
                and self.range_class(v)
                or v.toPython())
            for v in members]
        obj.__dict__[self.name] = val
        return val

    def __set__(self, obj, new_vals):
        log.debug("SET with descriptor value %s of type %s", new_vals, type(new_vals))
        if not isinstance(new_vals, (list, tuple)):
            raise AttributeError("to set a rdfList you must pass in `a` items (it can be `a` items of one)")
        try:
            old_vals = obj.__dict__[self.name]
        except KeyError:
            old_vals = []
            obj.__dict__[self.name] = old_vals
        old_head = obj.db.value(obj.resUri, self.pred)
        # This is a stack style where retrieval is opposite of how
        # it starts out
        # newnode = RDF.nil
        # for value in new_vals:
        #     almostnewnode = newnode
        #     newnode = BNode()
        #     obj.db.add((newnode, RDF.first, value2object(value)))
        #     obj.db.add((newnode, RDF.rest, almostnewnode))
        if not new_vals:
            new_head = RDF.nil
        else:
            new_head = BNode()
            new_tail = new_head
            old_tail = None
            for value in new_vals:
                if old_tail:
                    obj.db.add((old_tail, RDF.rest, new_tail))
                obj.db.add((new_tail, RDF.first, value2object(value)))
                old_tail = new_tail
                new_tail = BNode()
            obj.db.add((old_tail, RDF.rest, RDF.nil))
        obj.db.set((obj.resUri, self.pred, new_head))
        if old_head:
            rdfSubject(old_head)._remove(db=obj.db)
        obj.__dict__[self.name] = copy(new_vals)


class rdfContainer(rdfMultiple):
    """
    This is a Descriptor
    Expects to return a items of values (could be a items of one)

    container_type in `__init__` should be one of

               * rdf:Seq
               * rdf:Bag
               * rdf:Alt

    `__set__` will set the predicate as a RDF Container type
    (defaults to rdf:Seq)
    """

    def __init__(self, pred,  range_type=None, container_type="http://www.w3.org/1999/02/22-rdf-syntax-ns#Seq"):
        super().__init__(pred,  range_type=range_type)
        self.container_type = container_type

    def __get__(self, obj, cls):
        if obj is None:
            return self
        if self.name in obj.__dict__:
            return obj.__dict__[self.name]
        # log.debug("Geting %s for %s" % (
        #    obj.db.qname(self.pred),obj.db.qname(obj.resUri)))
        log.debug("Getting %s for %s", self.pred, obj.n3())
        base = obj.db.value(obj.resUri, self.pred)
        if not base:
            return []
        members = []
        i = 1
        first = obj.db.value(base, RDF._1)
        if not first:
            raise AttributeError(f"expected node [{base.n3()}] to be a items but it's not")
        while first:
            members.append(first)
            i += 1
            first = obj.db.value(base, RDF['_%d' % i])

        val = [(isinstance(v, (BNode, URIRef))
                and self.range_class(v)
                or v.toPython())
               for v in members]
        obj.__dict__[self.name] = val
        return val

    def __set__(self, obj, new_vals):
        log.debug("SET with descriptor value %s of type %s", new_vals, type(new_vals))
        if not isinstance(new_vals, (list, tuple)):
            raise AttributeError("to set a rdfList you must pass in `a` items (it can be `a` items of one)")
        seq = obj.db.value(obj.resUri, self.pred)
        if not seq:
            seq = BNode()
            obj.db.add((obj.resUri, self.pred, seq))
            obj.db.add((seq, RDF.type, RDF.Seq))
        for s, p, o in obj.db.triples((seq, None, None)):
            if p.startswith(RDF['_']):
                obj.db.remove((s, p, o))
                if isinstance(o, BNode) and o not in new_vals:
                    rdfSubject(o)._remove(db=obj.db)
        for i in range(len(new_vals)):
            obj.db.add((seq, RDF[f'_{i + 1}'], value2object(new_vals[i])))
        obj.__dict__[self.name] = copy(new_vals)


#
# More owl-ish and rdfs-ish descriptors

class owlTransitive(rdfMultiple):
    """
    owlTransitive is a descriptor based on a transitive predicate
    The predicate should be of type owl:TransitiveProperty
    """

    def __get__(self, obj, cls):
        if obj is None:
            return self
        if self.name in obj.__dict__:
            return obj.__dict__[self.name]
        log.debug("Getting with descriptor %s for %s", self.pred, obj.n3())
        val = [self.range_class(o)
               for o in obj.db.transitive_objects(obj.resUri, self.pred)]
        obj.__dict__[self.name] = val
        return val
