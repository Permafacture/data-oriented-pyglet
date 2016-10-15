'''
Class that wraps a numpy array as a buffer, and provides for resizing,
inserting, appending, and defragging.

This file is part of Numpy-ECS.
Copyright (C) 2016 Elliot Hallmark (permafacture@gmail.com)

Numpy-ECS is free software: you can redistribute it and/or modify
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
import numpy as np

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

class DefraggingArrayComponent(object):
    '''holds a resize-able, re-allocateable, numpy array buffer'''

    def __init__(self,name,dim,dtype,size=0):
      ''' create a numpy array buffer of shape (size,dim) with dtype==dtype'''
      #TODO: might could alternatively instatiate with an existing numpy array?
      self.name = name
      self.datatype=dtype #calling this dtype would be confusing because this is not a numpy array!
      self._dim = dim
      self.capacity = size
      if dim == (1,):
        self._buffer = np.empty(size,dtype=dtype) #shape = (size,) not (size,1)
        self.resize = self._resize_singledim
      elif dim > (1,): #dim is a tuple, not a scalar it seems
        self._buffer = np.empty((size,)+dim,dtype=dtype) #shape = (size,dim)
        self.resize = self._resize_multidim
      else:
        raise ValueError('''ArrayComponent dim must be >= 1''')

    #def resize(self,count):
    #    '''resize this component to new size = count'''
    #    #This is a placeholder, __init__ decides what to overwrite this with
    #    # ^ not true any more
    #    self._buffer= self._buffer.resize((count,)+self._dim)
        

    def assert_capacity(self,new_capacity):
        '''make certain Component is atleast `new_capcpity` big.
        resizing if necessary.'''
        if self.capacity < new_capacity:
            #print "change capacity:",self.capacity,"->", new_capacity
            self.resize(_nearest_pow2(new_capacity))
            self.capacity = new_capacity

    def realloc(self,old_selector,new_selector):
        self._buffer[new_selector] = self._buffer[old_selector]

    #def push_from_index(self,index,size):
    #    '''push all data in buffer from start onward forward by size.
    #    if size is negative, moves everything backwards.  Assumes alloc
    #    was already called, assuring that there is size empty values at
    #    end of buffer.'''
    #    end = self.capacity
    #    if size == 0:
    #        return
    #    elif size > 0:
    #        self._buffer[index+size:] = self._buffer[index:-size]
    #    elif size < 0:
    #        self._buffer[index+size:size] = self._buffer[index:]
 

    def __getitem__(self,selector):
      #assert self.datatype == self._buffer.dtype #bug if numpy changes dtype
      return self._buffer[selector]

    def __setitem__(self,selector,data):
      self._buffer[selector]=data
      assert self.datatype == self._buffer.dtype, 'numpy dtype may not change'

    def _resize_multidim(self,count):
      shape =(count,)+self._dim 
      try:
         #this try is because empty record arrays cannot be resized.
         #should be fixed in a more recent numpy.
         self._buffer.resize(shape)
      except ValueError:
         self._buffer = np.resize(self._buffer,shape)

    def _resize_singledim(self,count):
      try:
         #this try is because empty record arrays cannot be resized.
         #should be fixed in a more recent numpy.
         self._buffer.resize(count)
      except ValueError:
         self._buffer = np.resize(self._buffer,count)

    def __repr__(self):
      return "<DefraggingArrayComponent: %s>"%self.name

