#!/usr/bin/env python
"""
rdfalchemy.py - a Simple API for RDF


Requires rdflib <http://www.rdflib.net/> version 2.3 ??.

"""

__license__ = """
Copyright (c) 2005-2007 Philip Cooper <Philip.Cooper@openvest.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
__version__ = "0.2dev"

from rdflib import ConjunctiveGraph
from rdflib import Literal, BNode, Namespace, URIRef
from rdflib.Identifier import Identifier 
from rdflib.exceptions import *
import re

try:
    from hashlib import md5
except ImportError:
    from md5 import md5    

import logging
##console = logging.StreamHandler()
##formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
##console.setFormatter(formatter)
log=logging.getLogger('rdfalchemy')
##log.setLevel(logging.DEBUG)
##log.addHandler(console)

RDF  =Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
RDFS =Namespace("http://www.w3.org/2000/01/rdf-schema#")
OWL  =Namespace("http://www.w3.org/2002/07/owl#")

re_ns_n = re.compile('(.*[/#])(.*)')

    
# Look into caching as in:
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/276643
# Note: Non data descriptors (get only) lookup in obj.__dict__ first
#       Data descriptors (get and set) use the __get__ first


##################################################################################
# define our Base Class for all "subjects" in python 
##################################################################################

#class rdfSubject(object):
class rdfSubject(Identifier):
    db=ConjunctiveGraph()
    """Default graph for access to instances of this type"""
    rdf_type=None
    """rdf:type of instances of this class"""
    def __new__(cls, resUri = None, **kwargs):
        """docstring for __new__"""
        if not resUri or isinstance(resUri, BNode):
            sub = BNode.__new__(cls, resUri)
            sub.node_type = 'bnode'
        elif isinstance(resUri, (str, unicode)) and resUri.startswith("_:"):
            sub = BNode.__new__(cls, resUri[2:])
            sub.node_type = 'bnode'
        elif isinstance(resUri, URIRef):
            sub = URIRef.__new__(cls, resUri)
            sub.node_type = 'uri'
        elif isinstance(resUri, (str, unicode)) and resUri[0]=="<" and resUri[-1]==">":
            sub = URIRef.__new__(cls, resUri[1:-1])
            sub.node_type = 'uri'
        elif isinstance(resUri, rdfSubject):
            sub = Identifier.__new__(cls, resUri) 
            sub.node_type = resUri.node_type
            if sub.db != resUri.db:
               sub.db = resUri.db
        else:
            raise AttributeError("cannot construct rdfSubject from %s"%(str(resUri)))
        return sub

    def __init__(self, resUri = None, **kwargs):
        """The constructor tries hard to do return you an rdfSubject
        the parameter resUri can be:
         * an instance of an rdfSubject
         * an instance of a BNode or a URIRef
         * an n3 uriref string like: <urn:isbn:1234567890>
         * an n3 bnode string like _:xyz1234 
        a null resUri will cause a new one created of 
        this classes rdf_type
         `kwargs` is a set of values that will be set"""
        if kwargs:
            self._set_with_dict(kwargs)

        if not resUri:
            # lets create a new one
            if self.rdf_type:
                self.db.set((self,RDF.type, self.rdf_type))
        # lets get a default namespace for this 
        # ??obsolete ???
        rdftype = list(self.db.objects(self, RDF.type))
        if len(rdftype)==1:
            self.namespace, trash = re_ns_n.match(rdftype[0]).groups()
            self.namespace=Namespace(self.namespace)
        elif isinstance(self,URIRef):
            ns_n =  re_ns_n.match(self)
            if ns_n:
                self.namespace, self.name = ns_n.groups()
                self.namespace=Namespace(self.namespace)
                
    def n3(self):
        """n3 repr of this node"""
        if self.node_type == 'bnode':
            return "_:%s"%self
        elif self.node_type == 'uri':
            return "<%s>"%self
        else:
            raise AttributeError("Unknown node type for %s"(self))
        

    @classmethod
    def _getdescriptor(cls, key):
        """__get_descriptor returns the descriptor for the key.
        It essentially cls.__dict__[key] with recursive calls to super"""
        #log.debug("Getting descriptor for class: %s with key: %s" % (cls,key))
        # NOT SURE if mro is the way to do this or if we should call super or bases?
        for kls in cls.mro():
            if key in kls.__dict__:
                return kls.__dict__[key]
        raise AttributeError("descriptor %s not found for class %s" % (key,cls))
        
    #short term hack.  Need to go to a sqlalchemy 0.4 style query method
    # obj.query.get_by should map to obj.get_by  ..same for fetch_by
    @property
    def query(self):
        return self    

    @classmethod
    def get_by(cls, **kwargs):
        """Class Method, returns a single instance of the class
        by a single kwarg.  the keyword must be a descriptor of the
        class.
        example:
            bigBlue = Company.get_by(symbol='IBM')

        OWL Note:
            the keyword should map to an rdf predicate
            that is of type owl:InverseFunctional"""
        if len(kwargs) != 1:
            raise ValueError("get_by wanted eaactly 1 but got  %i args\nMaybe you wanted filter_by"%(len(kwargs)))
        key,value = kwargs.items()[0]
        if isinstance(value, URIRef) or isinstance(value,BNode) or isinstance(value,Literal):
            o = value
        else:
            o = Literal(value)
        pred=cls._getdescriptor(key).pred
        uri=cls.db.value(None,pred,o)
        if uri:
            return cls(uri)
        else:
            raise LookupError("%s = %s not found"%(key,value))

    @classmethod
    def filter_by(cls, **kwargs):
        """Class method returns a generator over classs instances
        meeting the kwargs conditions.

        Each keyword must be a class descriptor

        filter by RDF.type == cls.rdf_type is implicit

        Order helps, the first keyword should be the most restrictive
        """
        filters = []
        for key,value in kwargs.items():
            pred = cls._getdescriptor(key).pred
            # try to make the value be OK for the triple query as an object
            if isinstance(value, Identifier):
                obj = value
            else:
                obj = Literal(value)
            filters.append((pred,obj))
        # make sure we filter by type
        if not (RDF.type,cls.rdf_type) in filters:
            filters.append((RDF.type,cls.rdf_type))
        pred, obj = filters[0]
        log.debug("Checking %s, %s" % (pred,obj))
        for sub in cls.db.subjects(pred,obj):
            log.debug( "maybe %s" % sub )
            for pred,obj in filters[1:]:
                log.debug("Checking %s, %s" % (pred,obj))
                try:
                    cls.db.triples((sub,pred,obj)).next()
                except:
                    log.warn( "No %s" % sub )
                    break
            else:
                yield cls(sub)
        
    @classmethod
    def ClassInstances(cls):
        """return a generator for instances of this rdf:type
        you can look in MyClass.rdf_type to see the predicate being used"""
        for i in cls.db.subjects(RDF.type, cls.rdf_type):
            yield cls(i)

    @classmethod
    def GetRandom(cls):
        """for develoment just returns a random instance of this class"""
        from random import randint
        xii=list(cls.ClassInstances())
        return xii[randint(0,len(xii)-1)]
        
    def __repr__(self):
        return """%s('%s')""" % (self.__class__.__name__, self.n3())
    
    def __getitem__(self, pred):
        #log.debug("Getting with __getitem__ %s for %s"%(self.db.qname(pred),self.db.qname(self.resUri)))
        log.debug("Getting with __getitem__ %s for %s"%(pred,self.n3()))
        val=self.db.value(self,pred)
        if isinstance(val,Literal):
            val =  val.toPython() 
        elif isinstance(val, BNode) or isinstance(val,URIRef): 
            val=rdfSubject(val) 
        return val
        
    ## def __setitem__(self,pred,value):
    ## not even sure if this is a good idea here
        
    def __delitem__(self, pred):
        #log.debug("Deleting with __delitem__ %s for %s"%(self.db.qname(pred),self.db.qname(self.resUri)))
        log.debug("Deleting with __delitem__ %s for %s"%(pred,self))
        for s,p,o in self.db.triples((self, pred, None)):
            self.db.remove((s,p,o))
            #finally if the object in the triple was a bnode 
            #cascade delete the thing it referenced
            # ?? FIXME Do we really want to cascade if it's an rdfSubject??
            if isinstance(o,BNode) or isinstance(o,rdfSubject) and o.node_type == 'bnode':
                rdfSubject(o)._remove(db=self.db,cascade='bnode')
        
    def _set_with_dict(self, kv):
        """for each key,value pair in dict kv
               set self.key = value"""
        for key,value in kv.items():
            #item.__class__._getdescriptor('authors').__get__(item, item.__class__)
            descriptor = self.__class__._getdescriptor(key)
            descriptor.__set__(self, value)
        
        
    def _remove(self, node=None, db=None, cascade = 'bnode', bnodeCheck=True):
        """remove all triples where this rdfSubject is the subject of the triple
        db -- limit the remove operation to this graph
        node -- node to remove from the graph defaults to self
        cascade -- must be one of:
                    * none -- remove none
                    * bnode -- (default) remove all unreferenced bnodes
                    * all -- remove all unreferenced bnode(s) AND uri(s)
        bnodeCheck -- boolean 
                    * True -- (default) check bnodes and raise exception if there are
                              still references to this node
                    * False -- do not check.  This can leave orphaned object reference 
                               in triples.  Use only if you are resetting the value in
                               the same transaction
        """
        if not node:
            node = self
        log.debug("Called remove on %s" % node)
        if not db:
            db = self.db
        # we cannot delete a bnode if it is still referenced, 
        # i.e. if it is the o of a s,p,o 
        if bnodeCheck:
            if isinstance(node,BNode) or isinstance(node,rdfSubject) and node.node_type=='bnode':
                for s,p,o in db.triples((None,None,node)):
                    raise RDFAlchemyError("Cannot delete a bnode %s becuase %s still references it" % (node.n3(), s.n3()))
        # determine an appropriate test for cascade decisions
        if cascade == 'bnode':
            #we cannot delete a bnode if there are still references to it
            def test(node):
                if isinstance(node,(URIRef,Literal)) \
                   or isinstance(node,rdfSubject) and node.node_type <> 'bnode':
                    return False
                for s,p,o in db.triples((None,None,node)):
                        return False
                return True
        elif cascade == 'none':
            def test(node):
                return False
        elif cascade == 'all':
            def test(node):
                if not (isinstance(node,BNode) or isinstance(node,URIRef)):
                    return False
                for s,p,o in db.triples((None,None,node)):
                        return False
                return True
        else:
            raise AttributeError, "unknown cascade argument"
        for s,p,o in db.triples((node, None, None)):
            db.remove((s,p,o))
            if test(o):
                self._remove(node=o, db=db,cascade=cascade)
                
    def _rename(self, name, db=None):
        """rename a node """
        if not db:
            db = self.db
        if not (isinstance(name,BNode) or isinstance(name,URIRef)):
            raise AttributeError, ("cannot rename to %s" % name)
        for s,p,o in db.triples((self,None,None)):
            db.set((name, p, o))
        for s,p,o in db.triples((None,None,self)):
            db.set((s, p, name))
        self.resUri = name
        
        
    def _ppo(self,db=None):
        """Like pretty print...
        Return a 'pretty predicate,object' of self
        returning all predicate object pairs with qnames"""
        db = db or self.db
        for p,o in db.predicate_objects(self):
            print "%20s = %s"% (db.qname(p),str(o))
        print " "

    def md5_term_hash(self):
        d = md5(str(self))
        d.update("R")
        return d.hexdigest()
        
    

