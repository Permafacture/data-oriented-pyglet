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
from pyglet.graphics import allocation
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
#  array type, and that singles are the single type
#TODO: rename single attributes to indexed attributes or broadcastable.
class ArrayAttribute(object):
    '''holds a resize-able, re-allocateable, numpy array buffer
    for data that is many to one relationship with an object
    TODO: make reallocateable.'''

    def __init__(self,name,size,dim,dtype):
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

class SingleAttribute(object):
    '''holds a resize-able, re-allocateable, buffer
    for data that is one to one relationship with an object.
    TODO: make reallocateable (ie, for deletions)'''

    def __init__(self,name,dim,dtype):
      '''dtype -> numpy data type for array representation
         name -> property name to access from DataOriented Object'''
      self.name = name
      assert dim>=1, "SingleAttribute dimension: %s not >= 1" % (dim, )  
      self._dim = dim
      self.datatype=dtype
      self._buffer = np.array([],dtype=dtype)

    def __getitem__(self,selector):
      return self._buffer[selector]

    def __setitem__(self,selector,data):
      self._buffer[selector]=data

    def add(self,item):
      dim = self._dim
      if dim == 1:
        shape = (self._buffer.shape[0]+1,)
      else :
        shape = (self._buffer.shape[0]+1,dim)
      self._buffer.resize(shape)
      self._buffer[-1] = item
      return len(self._buffer) -1

    def __repr__(self):
      return self.name

class DataDomain(object):
    '''
    Manages arrays of properties.
    "objects" are added through this and an accessor is returned which allows
    for object oriented interaction with entries in the data domain
    '''

    def __init__(self,size=16):
      self.allocator = allocation.Allocator(size)
      self._id2index_dict = {}
      self._next_id = 0


      self.indices = ArrayAttribute('indices',size,1,np.int32)

      #arrayed data
      self.array_attributes = [self.indices]

      #property data
      self.single_attributes = []
 
      #__init__ of subclasses should do this:
      #self.DataAccessor = self.generate_accessor('GenericDataAccessor')

    def safe_alloc(self, count):
      '''Allocate space in arrays, resizing them if necessary.'''
      try:
          return self.allocator.alloc(count)
      except allocation.AllocatorMemoryException, e:
          capacity = _nearest_pow2(e.requested_capacity)
          #self._version += 1
          for attribute in self.array_attributes:
              attribute.resize(capacity)
          self.allocator.set_capacity(capacity)
          return self.allocator.alloc(count)

    def generate_accessor(self,name):
        '''construct the DataAccessor specific for this DataDomain'''
        return data_accessor_factory(name,self,
                        self.array_attributes,self.single_attributes)
 

    def index_from_id(self,id):
        return self._id2index_dict[id]

    def get_selector(self):
        '''return a slice or mask that can be used to access only the valid
        portions of the buffers'''
        #TODO allocator should return a selector for valid memory locations
        # initially, since all data will be tightly packed, this can be a slice.
        # eventually, if Data Oriented Objects become resizeable and thus have
        # space overprovisioned for them between elements in the buffer, this 
        # could be a mask.
        starts,sizes = self.allocator.get_allocated_regions()
        end = starts[-1]+sizes[-1]
        return slice(0,end,1)


    def add(self,*args,**kwargs):
      '''add an instance of properties to the domain.
      returns a data accessor to allow for interaction with this instance of 
      data.'''  
      
      #TODO tidy this up by making a finalize method that __init__ calls that
      # creates the DataAccessor and sets of arrayed and single names.
      # finalize might also handle discovering if this domain has any
      # SingleAttributes and decide between two `add`s, where one expects 
      # not to have SingleAttributes and the other does.  ie: no indices
      # right now, assumes at least one SingleAttribute
      n = None; index = None
      arrayed_names = {attr.name for attr in self.array_attributes}
      single_names  = {attr.name for attr in self.single_attributes}
      assert single_names, "DataDomains without one SingleAttribute not yet supported"

      for key,val in kwargs.items():
        if key in single_names:
          if index is None:
            index = getattr(self,key).add(val)
          else:
            getattr(self,key).add(val)

      for key,val in kwargs.items():
        if key in arrayed_names:
          if n is None:
            n = len(val)
            start = self.safe_alloc(n)
            selector = slice(start,start+n,1)
          getattr(self,key)[selector] = val

      self.indices[selector] = index
      id =self._next_id 
      self._id2index_dict[id] = index
      self._next_id += 1

      return self.DataAccessor(self,id)

