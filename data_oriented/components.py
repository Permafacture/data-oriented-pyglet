'''
Class that wraps a numpy array as a buffer, and provides for resizing,
inserting, appending, and defragging.
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
      if dim == (1,):
        dim = ()
      self._dim = dim
      self.capacity = size

      if dim == 1:
        self._buffer = np.empty(size,dtype=dtype) #shape = (size,) not (size,1)
        self.resize = self._resize_singledim
      elif dim > 1:
        self._buffer = np.empty((size,)+dim,dtype=dtype) #shape = (size,dim)
        self.resize = self._resize_multidim
      else:
        raise ValueError('''ArrayComponent dim must be >= 1''')

    def resize(self,count):
        '''resize this component to new size = count'''
        #This is a placeholder, __init__ decides what to overwrite this with


    def alloc(self,size):
        '''make certain Component can accept `size` new values
        resizing if necessary. `size` <= 0 will not have and effect'''
        print "allocating %s to %s"%(size,self.name)
        new_capacity = len(self._buffer)+size
        if self.capacity < new_capacity:
            self.resize(_nearest_pow2(new_capacity))
            self.capacity = new_capacity

    def realloc(self,old_selector,new_selector):
        self._buffer[new_selector] = self._buffer[old_selector]

    def push_from_index(self,index,size):
        '''push all data in buffer from start onward forward by size.
        if size is negative, moves everything backwards.  Assumes alloc
        was already called, assuring that there is size empty values at
        end of buffer.'''
        end = self.capacity
        if size == 0:
            return
        elif size > 0:
            self._buffer[index+size:] = self._buffer[index:-size]
        elif size < 0:
            self._buffer[index+size:size] = self._buffer[index:]
 

    def __getitem__(self,selector):
      #assert self.datatype == self._buffer.dtype #bug if numpy changes dtype
      return self._buffer[selector]

    def __setitem__(self,selector,data):
      self._buffer[selector]=data
      assert self.datatype == self._buffer.dtype, 'numpy dtype has not changed'

    def _resize_multidim(self,count):
      self._buffer.resize((count,)+self._dim)

    def _resize_singledim(self,count):
      self._buffer.resize(count)

    def __repr__(self):
      return "<DefraggingArrayComponent: %s>"%self.name

