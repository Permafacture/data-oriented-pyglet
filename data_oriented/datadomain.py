'''
Data Oriented ORM

This file is part of Data Oriented Python.
Copyright (C) 2016 Elliot Hallmark (permfacture@gmail.com)

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

#TODO: datadomain.arrayattributes.extend/append should assert that it is an
#  array type, and that broadcastables are the broadcastable type
#TODO: rename single attributes to indexed attributes or broadcastable.
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
      #print "get buffer",self.datatype,self._buffer.dtype #TODO assert this
      return self._buffer[selector]

    def __setitem__(self,selector,data):
      #print "set buffer1",self.datatype,self._buffer.dtype #TODO assert this
      self._buffer[selector]=data
      #print "set buffer2",self.datatype,self._buffer.dtype

    def _resize_multidim(self,count):
      self._buffer.resize((count,self._dim))

    def _resize_singledim(self,count):
      self._buffer.resize(count)

class BroadcastableAttribute(object):
    '''holds a resize-able, re-allocateable, buffer
    for data that is one to one relationship with an object.
    TODO: make reallocateable (ie, for deletions)'''

    #TODO, this became the same thing as an ArrayAttribute. the only difference
    # is in how a user intends to deal with them.  So, get rid of duplication.
    def __init__(self,name,dim,dtype,size=allocation.DEFAULT_SIZE):
      '''dtype -> numpy data type for array representation
         name -> property name to access from DataOriented Object'''
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
      return self._buffer[selector]

    def __setitem__(self,selector,data):
      self._buffer[selector]=data

    def _resize_multidim(self,count):
      self._buffer.resize((count,self._dim))

    def _resize_singledim(self,count):
      self._buffer.resize(count)

    #def add(self,item):
    #  dim = self._dim
    #  if dim == 1:
    #    shape = (self._buffer.shape[0]+1,)
    #  else :
    #    shape = (self._buffer.shape[0]+1,dim)
    #  self._buffer.resize(shape)
    #  self._buffer[-1] = item
    #  return len(self._buffer) -1

    def __repr__(self):
      return self.name

class DataDomain(object):
    '''
    Manages arrays of properties.
    "objects" are added through this and an accessor is returned which allows
    for object oriented interaction with entries in the data domain
    '''

    def __init__(self):
      self.allocator = allocation.ArrayAndBroadcastableAllocator()
      self.dealloc = self.allocator.dealloc
      self.index_from_id = self.allocator.index_from_id
      self.slice_from_id = self.allocator.slice_from_id

      self._next_id = 0


      self.indices = ArrayAttribute('indices',1,np.int32)

      #arrayed data
      self.array_attributes = [self.indices]

      #property data
      self.broadcastable_attributes = []
 
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

    def generate_accessor(self,name):
        '''construct the DataAccessor specific for this DataDomain'''
        return data_accessor_factory(name,self,
                        self.array_attributes,self.broadcastable_attributes)
 

    #def index_from_id(self,id):
    #    return self.allocator.index_from_id(id)

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
        for id,idx,selector in self.allocator.iter_selectors():
            indices[selector] = idx

   # def mark_attributes_as_dirty(self,fragmented=True):
   #     '''Since we rely on efficiently using arrays when they are clean
   #     and changing the pointers to various array accessing functions
   #     after they are dirtied, this function encapsulates all the
   #     dirty marking logic.  Some operations don't fragment the buffers
   #     so we can avoid marking them as needing defragmentation with the
   #     `fragmented=False` kwarg.

   #     creates and manages `array_selector`, `broadcastable_selector`, and
   #     `as_array`
   #     '''
   #     self._array_selector = None
   #     self._broadcastable_selector = None
   #     if fragmented:
   #         self._as_array = self._get_dirty_array

   # @property
   # def array_selector(self):
   #     '''return the selector to all valid data in the ArrayAttributes'''
   #     if self._array_selector: return self._array_selector
   #     a = self.allocator.array_allocator
   #     start = a.starts[-1]
   #     array_selector = slice(start,start+a.sizes[-1],1)
   #     self._array_selector = array_selector
   #     return array_selector

   # @property
   # def broadcastable_selector(self):
   #     '''return the selector to all valid data in the BroadcastableAttributes'''
   #     if self._broadcastable_selector: return self._broadcastable_selector
   #     a = self.allocator.broadcast_allocator
   #     #b_selector = slice(start,start+a.sizes[-1],1)
   #     b_selector = a.starts[-1] #start = a.starts[-1]
   #     self._broadcastable_selector = b_selector
   #     return b_selector

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
        if isinstance(attr,ArrayAttribute):
          return attr[array_selector]
        elif isinstance(attr,BroadcastableAttribute):
          #TODO: hiding broadcasting from user at the cost of making access
          # to unbroadcasted arrays difficult is dumb.  fix this soon and
          # add an as_broadcasted or something.
          return attr[self.indices[array_selector]]
        else:
          raise ValueError(
                "Cannot return non Attribute type %s as an array" % type(attr))
    
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

