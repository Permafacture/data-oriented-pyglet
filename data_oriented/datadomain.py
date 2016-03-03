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
from accessors import data_accessor_factory

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

    def __init__(self,name,dim,dtype,size=allocation.DEFAULT_SIZE):
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

    def __getitem__(self,selector):
      #assert self.datatype == self._buffer.dtype #bug if numpy changes dtype
      return self._buffer[selector]

    def __setitem__(self,selector,data):
      self._buffer[selector]=data
      assert self.datatype == self._buffer.dtype #bug if numpy changes dtype

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

    def safe_alloc(self, count,id):
      '''Allocate space in arrays, resizing them if necessary.

      returns: `array_start` which is the first index in the ArrayAttributes 
      that can accept data of size=count '''
      try:
          array_start = self.allocator.alloc(id,count)
      except allocation.AllocatorMemoryException, e:
          capacity = _nearest_pow2(e.requested_capacity)
          #self._version += 1
          for attribute in self.array_attributes:
              attribute.resize(capacity)
          for accessor in self.registered_domains:
              accessor.resize(capacity)
          self.allocator.set_capacity(capacity)
          array_start = self.allocator.alloc(id,count)
      return array_start

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
        return data_accessor_factory(name,self,self.array_attributes,[])
 

    def defragment_attributes(self):
        array_fixers = self.allocator.defrag()
        for attribute in self.array_attributes:
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

    def add_empty(self,size):
        '''create space in attribute arrays without initializing the data'''
        id =self._next_id 
        self._next_id += 1
        array_start = self.safe_alloc(size,id)
        return self.DataAccessor(self,id)
        

    def add(self,*args,**kwargs):
        '''add an instance of properties to the domain.
        returns a data accessor to allow for interaction with this instance of 
        data.'''  
        
        id =self._next_id 
        self._next_id += 1

        #TODO this could be more efficient.
        n = None
        arrayed_names = {attr.name for attr in self.array_attributes}
        for key,val in kwargs.items():
          if key in arrayed_names:
            if n is None:
              n = len(val)
              array_start = self.safe_alloc(n,id)
              selector = slice(array_start,array_start+n,1)
            getattr(self,key)[selector] = val

        return self.DataAccessor(self,id)

class BroadcastingDataDomain(object):
    '''
    Manages arrays of properties.  BroadcastableAttributes map one-to-many
    to ArrayAttributes.
  
    "objects" are added through this and an accessor is returned which allows
    for object oriented interaction with entries in the data domain
    '''

    def __init__(self):
      self.allocator = allocation.ArrayAndBroadcastableAllocator()
      self.dealloc = self.allocator.dealloc
      #self.selector_from_id = self.allocator.selector_from_id

      self._next_id = 0


      self.indices = ArrayAttribute('indices',1,np.int32)

      #arrayed data
      self.array_attributes = [self.indices]

      #property data
      self.broadcastable_attributes = []
      self.registered_domains = [] 
      #__init__ of subclasses should do this:
      #self.DataAccessor = self.generate_accessor('GenericDataAccessor')

    def safe_alloc(self, count,id):
      '''Allocate space in arrays, resizing them if necessary.
      assumes that BroadcastableAttributes are having only
      one element added.

      returns: (array_start, free_index) where array start is the first index
      in the ArrayAttributes that can accept date of size=count and free_index
      is the first index in the BroadcastableAttributes that can accept a 
      value '''
      try:
          array_start = self.allocator.alloc_array(id,count)
      except allocation.AllocatorMemoryException, e:
          capacity = _nearest_pow2(e.requested_capacity)
          #self._version += 1
          for attribute in self.array_attributes:
              attribute.resize(capacity)
          self.allocator.set_array_capacity(capacity)
          array_start = self.allocator.alloc_array(id,count)
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


#TODO Register domain should assert that the other domains are size zero
#Empty_add create a zero sized accessor
#Accessors need to grow themselves
#safe_alloc needs to call that
    def register_domain(self,domain):
        '''register another DataDomain to be accessed from within this one
        and return a DataAccessor through which to access it'''
        try:
          size = self.allocator.last_valid_index()
        except IndexError:
          size=0
        accessor = domain.add_empty(size) 
        self.registered_domains.append(accessor)
        return accessor

    def generate_accessor(self,name):
        '''construct the DataAccessor specific for this DataDomain'''
        attributes = []
        allocators = []
        attributes.extend(self.array_attributes)
        allocators.extend([self.allocator.array_allocator]*len(self.array_attributes))
        attributes.extend(self.broadcastable_attributes)
        allocators.extend([self.allocator.broadcast_allocator]*len(self.broadcastable_attributes))

        return data_accessor_factory(name,self,attributes,allocators)
 

    def defragment_attributes(self):
        array_fixers, broadcastable_fixers = self.allocator.defrag()
        for attribute in self.array_attributes:
          for source_sel, target_sel in zip(*array_fixers):
            attribute[target_sel] = attribute[source_sel]
        for attribute in self.broadcastable_attributes:
          for source_sel, target_sel in zip(*broadcastable_fixers):
            attribute[target_sel] = attribute[source_sel]
        #TODO this below and the allocator function that enables it seem inefficient...
        indices=self.indices
        for id,selector in self.allocator.iter_selectors():
            indices[selector] = idx

    def as_array(self,attr):
        '''Placeholder function.  datadomain.as_array should point to 
        _get_dirty_array or _get_defragged_array depending on if the 
        attributes are currently fragmented or not'''

        #don't give the user a function that might overwrite itself to become
        # more efficient, because the user may keep calling the inefficient 
        # one! This extra level of function call is not ideal, but better than
        # letting the user call _get_dirty_array over and over accidentally.
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
        array_start = self.safe_alloc(size,id)
        return self.DataAccessor(self,id)

    def add(self,*args,**kwargs):
      '''add an instance of properties to the domain.
      returns a data accessor to allow for interaction with this instance of 
      data.'''  
      
      #TODO tidy this up by making a finalize method that __init__ calls that
      # creates the DataAccessor and sets of arrayed and broadcastable names.
      # finalize might also handle discovering if this domain has any
      # BroadcastableAttributes and decide between two `add`s, where one expects 
      # not to have BroadcastableAttributes and the other does.  ie: no indices
      # right now, assumes at least one BroadcastableAttribute

      id =self._next_id 
      self._next_id += 1

      #TODO this could be more efficient.
      n = None
      arrayed_names = {attr.name for attr in self.array_attributes}
      broadcastable_names  = {attr.name for attr in self.broadcastable_attributes}
      assert broadcastable_names, "DataDomains without one BroadcastableAttribute not yet supported"

      for key,val in kwargs.items():
        if key in arrayed_names:
          if n is None:
            n = len(val)
            array_start,free_index = self.safe_alloc(n,id)
            selector = slice(array_start,array_start+n,1)
          getattr(self,key)[selector] = val

      for key,val in kwargs.items():
        if key in broadcastable_names:
          getattr(self,key)[free_index] = val


      self.indices[selector] = free_index

      return self.DataAccessor(self,id)

