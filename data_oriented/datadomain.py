'''
Data Oriented ORM

This file is part of Data Oriented Python.
Copyright (C) 2016 Elliot Hallmark (permafacture@gmail.com)

Data Oreinted Python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

Data Oriented Python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''


#TODO: 
#  pyglet probably has the domain versioning for a good reason. Figure out
#    what exactly and likely implement it here.

#  come up with better names for the Attribute types
import numpy as np
from pyglet import gl
import allocation
from math import pi, sin, cos,atan2,sqrt
from accessors import data_accessor_factory, DataAccessor

def _nearest_pow2(v):
    # From http://graphics.stanford.edu/~seander/bithacks.html#RoundUpPowerOf2
    # Credit: Sean Anderson
    v -= 1
    v |= v >> 1
    v |= v >> 2
    v |= v >> 4
    v |= v >> 8
    v |= v >> 16
    return v + 1

class ArrayAttribute(object):
    '''holds a resize-able, re-allocateable, numpy array buffer
    for data that is many to one relationship with an object
    TODO: make reallocateable.'''

    def __init__(self,name,dim,dtype,size=0):
      ''' create a numpy array buffer of shape (size,dim) with dtype==dtype'''
      #TODO: might could alternatively instatiate with an existing numpy array?
      self.name = name
      self.datatype=dtype #calling this dtype would be confusing because this is not a numpy array!
      self._dim = dim
      if dim == 1:
        self._buffer = np.empty(size,dtype=dtype) #shape = (size,) not (size,1)
        self.resize = self._resize_singledim
      elif dim > 1:
        self._buffer = np.empty((size,dim),dtype=dtype) #shape = (size,dim)
        self.resize = self._resize_multidim
      else:
        raise ValueError('''ArrayAttribute dim must be >= 1''')

    def resize(self,count):
        '''resize this accessor to new size = count'''
        #This is a placeholder, __init__ decides what to overwrite this with

    def __getitem__(self,selector):
      #assert self.datatype == self._buffer.dtype #bug if numpy changes dtype
      return self._buffer[selector]

    def __setitem__(self,selector,data):
      self._buffer[selector]=data
      assert self.datatype == self._buffer.dtype, 'numpy dtype has not changed'

    def _resize_multidim(self,count):
      self._buffer.resize((count,self._dim))

    def _resize_singledim(self,count):
      self._buffer.resize(count)

    def __repr__(self):
      return "<Array Attribute: %s>"%self.name



class DataDomain(object):
    '''
    Manages arrays of properties.
  
    "objects" are added through this and an accessor is returned which allows
    for object oriented interaction with entries in the data domain
    '''

    def __init__(self):
      self.allocator = allocation.DefraggingAllocator()
      self.dealloc = self.allocator.dealloc
      #self.selector_from_id = self.allocator.selector_from_id

      self._next_id = 0

      self.array_attributes = []
      self.registered_domains = [] #accessors to sections of other DataDomains
      #__init__ of subclasses should do this:
      #self.DataAccessor = self.generate_accessor('GenericDataAccessor')

    def safe_alloc(self, id, count):
      '''Allocate space in arrays, resizing them if necessary.

      returns: `array_start` which is the first index in the ArrayAttributes 
      that can accept data of size=count '''
      #print "data safe_alloc:",id
      try:
          array_start = self.allocator.alloc(id,count)
      except allocation.AllocatorMemoryException, e:
          capacity = _nearest_pow2(e.requested_capacity)
          #self._version += 1
          #Why isn't this valid? for attribute in self.array_attributes if isinstance(attribute,ArrayAttribute):
          for attribute in ( a for a in self.array_attributes if isinstance(a,ArrayAttribute)):
              attribute.resize(capacity)
          self.allocator.set_capacity(capacity)
          array_start = self.allocator.alloc(id,count)
      return array_start

      reg_d = self.registered_domains
      if reg_d:
        for accessor in reg_d:
          accessor.resize(count)

    def safe_dealloc(self,id):
        #print "data safe dealloc:",id
        array_size = self.allocator.array_allocator.size_from_id(id)
        self.allocator.dealloc(id)
        for accessor in self.registered_domains:
          accessor.resize(-array_size) 

    def safe_realloc(self,id,count):
        '''reallocate space in arrays. If count is None, deallocate the space'''
        #print "Data safe_realloc:",id
        #Must get old size before deallocating, even if not reallocating
        old_size = self.allocator.size_from_id(id)
        self.allocator.dealloc(id)
        if count is not None:
          self.safe_alloc(id, old_size+count)

    def register_domain(self,domain):
        '''register another DataDomain to be accessed from within this one
        and return a DataAccessor through which to access it'''
        size = self.allocator.capacity
        assert size == 0 #right now, must register while this domain is empty
        #^why would you register a new domain at any other point than __init__
        accessor = domain.add_empty(size) #an accessor to the *other* domain
        self.registered_domains.append(accessor)
        return accessor
 

    def generate_accessor(self,name):
        '''construct the DataAccessor specific for this DataDomain'''
        #TODO condense this

        attributes = []
        allocators = []
        attributes.extend(self.array_attributes)
        allocators.extend([self.allocator]*len(self.array_attributes))
        return data_accessor_factory(name,self,attributes,allocators)
 

    def defragment_attributes(self):
        array_fixers = self.allocator.defrag()
        for attribute in self.array_attributes:
          if isinstance(attribute,ArrayAttribute):
            for source_sel, target_sel in zip(*array_fixers):
              attribute[target_sel] = attribute[source_sel]
              attribute[target_sel] = attribute[source_sel]

    def as_array(self,attr):
        '''return a numpy array view on an attribute'''
        if self.allocator.dirty:
          self.defragment_attributes()
        return self._as_array(attr)

    def _as_array(self,attr):
        '''return the valid portions of the attribute buffer.'''

        array_selector = slice(0, self.allocator.all_valid_selector(),1)
        if isinstance(attr,ArrayAttribute):
          return attr[array_selector]
        else:
          raise ValueError(
                "Cannot return non Attribute type %s as an array" % type(attr))

    def add_empty(self,size): #TODO is this only ever used to make zero sized arrays?
        #     see 
        '''create space in attribute arrays without initializing the data'''
        id =self._next_id 
        self._next_id += 1
        array_start = self.safe_alloc(id,size)
        return self.DataAccessor(self,id)
        

    def add(self,*args,**kwargs):
      '''add an instance of properties to the domain.
      returns a data accessor to allow for interaction with this instance of 
      data.'''  

      id =self._next_id 
      self._next_id += 1
      
      #TODO tidy this up by making a finalize method that __init__ calls that
      # creates the DataAccessor and sets of arrayed and broadcastable names.
      n = None
      arrayed_attr_names = [attr.name for attr in self.array_attributes]

      for key in arrayed_attr_names:
          try: val = kwargs[key]
          except KeyError as e:
            raise KeyError("expected kwarg '%s' not provided" % (key,)) 
          if n is None:
            n = len(val)
            array_start,free_index = self.safe_alloc(id,n)
            selector = slice(array_start,array_start+n,1)
          getattr(self,key)[selector] = val

      #TODO add should beable to pass optional keyword args to set the values
      # of these inherited attributes.  Right now this relies on child domain
      # updating these values before the parent does math on the array.
      for accessor in self.registered_domains:
          accessor.resize(n)

      return self.DataAccessor(self,id)

class BroadcastingDataDomain(object):
    '''
    Manages arrays of properties.  broadcastable_attributes map one-to-many
    to array_attributes.
  
    "objects" are added through this and an accessor is returned which allows
    for object oriented interaction with entries in the data domain
    '''

    def __init__(self):
      #TODO don't have a seperate allocator, just have two allocators here.
      self.allocator = allocation.ArrayAndBroadcastableAllocator()
      #self.selector_from_id = self.allocator.selector_from_id

      self._next_id = 0


      self.indices = ArrayAttribute('indices',1,np.int32)

      #arrayed data
      self.array_attributes = [self.indices]

      #property data
      self.broadcastable_attributes = []
      self.registered_domains = []
      #TODO is this comment currently accurate?
      #__init__ of subclasses should do this:
      #self.DataAccessor = self.generate_accessor('GenericDataAccessor')

    def safe_alloc(self, id, count):
      '''Allocate space in arrays, resizing them if necessary.
      assumes that broadcastable_attributes are having only
      one element added and all registered domains are array_attributes

      returns: (array_start, free_index) where array start is the first index
      in the ArrayAttributes that can accept date of size=count and free_index
      is the first index in the BroadcastableAttributes that can accept a 
      value '''
      try:
          #print "alloc:",id,count
          array_start = self.allocator.alloc_array(id,count)
      except allocation.AllocatorMemoryException, e:
          capacity = _nearest_pow2(e.requested_capacity)
          #self._version += 1
          for attribute in self.array_attributes:
              attribute.resize(capacity)
          self.allocator.set_array_capacity(capacity)
          array_start = self.allocator.alloc_array(id,count)

      reg_d = self.registered_domains
      if reg_d:
        for accessor in reg_d:
          accessor.resize(count)


      try:
          free_index = self.allocator.alloc_broadcastable(id)
      except allocation.AllocatorMemoryException, e:
          capacity = _nearest_pow2(e.requested_capacity)
          #self._version += 1
          for attribute in self.broadcastable_attributes:
              attribute.resize(capacity)
          self.allocator.set_broadcastable_capacity(capacity)
          free_index = self.allocator.alloc_broadcastable(id)
      return (array_start,free_index)

    def safe_dealloc(self,id):
        #print "Broad safe dealloc"
        array_size = self.allocator.array_allocator.size_from_id(id)
        self.allocator.dealloc(id)
        for accessor in self.registered_domains:
          accessor.resize(-array_size) 

    def safe_realloc(self,id,count):
        '''reallocate space in arrays. If count is None, deallocate the space'''
        #Must get old size before deallocating, even if not reallocating
        #print "Broad safe realloc"
        #TODO I don't think count=None is necessary any more. just dealloc
        old_size = self.allocator.array_allocator.size_from_id(id)
        assert (count and old_size-count >=0), "can't realloc to a negative size" 
        self.safe_dealloc(id)
        if count is not None:
          self.safe_alloc(id, old_size+count,1)

    def register_domain(self,domain,allocator):
        '''register another DataDomain to be accessed from within this one
        through an allocator, 
        and return a DataAccessor through which to access it'''
        size = allocator.capacity
        assert size == 0 #right now, must register while this domain is empty
        #^why would you register a new domain at any other point than __init__
        accessor = domain.add_empty(size) #an accessor to the *other* domain
        self.registered_domains.append(accessor)
        return accessor

    def generate_accessor(self,name):
        '''construct the DataAccessor specific for this DataDomain'''
        attributes = []
        allocators = []
        attributes.extend(self.array_attributes)
        allocators.extend([
          self.allocator.array_allocator]*len(self.array_attributes))
        attributes.extend(self.broadcastable_attributes)
        allocators.extend([self.allocator.broadcast_allocator]*len(
                            self.broadcastable_attributes))

        return data_accessor_factory(name,self,attributes,allocators)
 

    def defragment_attributes(self):
        #TODO don't put accessors in array_attributes!
        array_fixers, broadcastable_fixers = self.allocator.defrag()
        for attribute in self.array_attributes:
            for source_sel, target_sel in zip(*array_fixers):
              attribute[target_sel] = attribute[source_sel]
        for attribute in self.broadcastable_attributes:
            for source_sel, target_sel in zip(*broadcastable_fixers):
              attribute[target_sel] = attribute[source_sel]
        #TODO this below and the allocator function that enables it seem inefficient...
        indices=self.indices
        for idx,selector in self.allocator.iter_selectors():
            indices[selector] = idx

    def as_array(self,attr):
        '''Return a numpy.array view on an attribute, defragging if necessary'''
        if self.allocator.dirty:
          self.defragment_attributes()
        return self._as_array(attr)

    def _as_array(self,attr):
        '''datadomain calls this as `as_array` when it knows the attributes
        are not fragmented.

        Helper function to return the valid portions of the attribute 
        buffer.  BroadcastableAttributes are broadcasted to be used with
        the ArrayAttributes here'''

        array_selector = slice(0, self.allocator.array_selector(),1)
        if attr in self.array_attributes:
          return attr[array_selector]
        elif attr in self.broadcastable_attributes:
          #TODO: hiding broadcasting from user at the cost of making access
          # to unbroadcasted arrays difficult is dumb.  fix this soon and
          # add an as_broadcasted or something.
          return attr[self.indices[array_selector]]
        else:
          raise ValueError(
                "Cannot return non Attribute type %s as an array" % type(attr))
    
    def add_empty(self,size):
        '''create space in attribute arrays without initializing the data'''
        id =self._next_id 
        self._next_id += 1
        array_start = self.safe_alloc(id,count)
        return self.DataAccessor(self,id)

    def add(self,*args,**kwargs):
      '''add an instance of properties to the domain.
      returns a data accessor to allow for interaction with this instance of 
      data.'''  

      id =self._next_id 
      self._next_id += 1
      
      #TODO tidy this up by making a finalize method that __init__ calls that
      # creates the DataAccessor and sets of arrayed and broadcastable names.
      # finalize might also handle discovering if this domain has any
      # BroadcastableAttributes and decide between two `add`s, where one expects 
      # not to have BroadcastableAttributes and the other does.  ie: no indices
      # right now, assumes at least one BroadcastableAttribute

      #TODO this could be more efficient.
      #TODO is it a mistake to resize accessors here? maybe it should be up 
      #  to the caller to add to the registered domains
      n = None
      #arrayed_attr_names = [attr.name for attr in self.array_attributes if isinstance(attr,ArrayAttribute)]
      #arrayed_attr_names.remove('indices')
      #arrayed_accessors = [attr for attr in self.array_attributes if isinstance(attr,DataAccessor)]
      #broad_attr_names = [attr.name for attr in self.broadcastable_attributes if isinstance(attr,ArrayAttribute)]
      #broad_accessors = [attr for attr in self.broadcastable_attributes if isinstance(attr,DataAccessor)]
      arrayed_attr_names = [attr.name for attr in self.array_attributes]
      arrayed_attr_names.remove('indices')
      broad_attr_names = [attr.name for attr in self.broadcastable_attributes ]
     
      #broadcastable_names  = {attr.name for attr in self.broadcastable_attributes if isinstance(attr,ArrayAttribute}
      assert broad_attr_names, "DataDomains without one BroadcastableAttribute not yet supported"

      #TODO should datadomains export attributes? 
      for key in arrayed_attr_names:
          try: val = kwargs[key]
          except KeyError as e:
            raise KeyError("expected kwarg '%s' not provided" % (key,)) 
          if n is None:
            n = len(val)
            array_start,free_index = self.safe_alloc(id,n)
            selector = slice(array_start,array_start+n,1)
          getattr(self,key)[selector] = val

      for key in broad_attr_names:
          try: val = kwargs[key]
          except KeyError as e:
            raise KeyError("expected kwarg '%s' not provided" % (key,)) 
          getattr(self,key)[free_index] = val

      self.indices[selector] = free_index


      return self.DataAccessor(self,id)

