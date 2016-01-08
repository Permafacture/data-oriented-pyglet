#!/usr/bin/env python

"""
accumulator class

Designed to be used as an expandable numpy array, to accumulate values, rather
than a python list.

Note that slices return copies, rather than views, unlike regular numpy arrays.
This is so that the buffer can be re-allocated without messing up any views.

"""
import numpy as np

class Accumulator(object):
    #A few parameters
    DEFAULT_BUFFER_SIZE = 128
    BUFFER_EXTEND_SIZE = 1.25 # array.array uses 1+1/16 -- that seems small to me.
    def __init__(self, obj=(), dtype=None, length=None):
        """
        instantiate an accumulator:

        :param obj=(): An object to make an accumulator from. should be a sequence.
                       No object with create an empty Accumulator. It will build
                       a sequence similarly to numpy.array

        :param dytype=None: the dtype to use for the Accumulator. If None, it will
                           be auto-determined from the data types in obj, defaulting
                           to np.float64

        :param length=None: initial length to make the internal buffer. Default is 128 elements.
        :type length: integer

        note: a scalar accumulator doesn't really make sense, so you get a length-1 array instead.
        """        
        try:
            l = len(obj)
        except TypeError: # probably a scalar
            obj = (obj,) # wrap it in a tuple

        if len(obj) == 0:
            # create a length zero array
            # with complex dtypes, the np.array() doesn't like empty tuples..
            buffer = np.empty((0,), dtype=dtype)
        else:
            # create buffer from input object
            buffer = np.array(obj, dtype=dtype, copy=True)

        if buffer.ndim > 1:
            raise ValueError("accumulator only works with 1-d data")
        buffer.shape = (-1) # to make sure we don't have a scalar
        self.length = buffer.shape[0]
        ## add the padding to the buffer
        buffer.resize( max(self.DEFAULT_BUFFER_SIZE, self.length*self.BUFFER_EXTEND_SIZE) )

        self.__buffer = buffer

    @property
    def dtype(self):
        return self.__buffer.dtype

    @property
    def buffersize(self):
        """
        the size of the internal buffer
        """
        return self.__buffer.size

    @property
    def shape(self):
        """
        To be compatible with ndarray.shape
        (only the getter!) 
        """
        return (self.length,)
    
    def __len__(self):
        return self.length
        
    def __array__(self, dtype=None):
        """
        a.__array__(|dtype) -> copy of array.
    
        Always returns a copy array, so that buffer doesn't have any references to it.
        """
        return np.array(self.__buffer[:self.length], dtype=dtype, copy=True)

    def append(self, item):
        """
        add a new item to the end of the array
        """
        try:
            self.__buffer[self.length] = item
            self.length += 1
        except IndexError: # the buffer is not big enough
            self.resize(self.length*self.BUFFER_EXTEND_SIZE)
            self.append(item)

    def extend(self, items):
        """
        add a sequence of new items to the end of the array
        """
        try:
            self.__buffer[self.length:self.length+len(items)] = items
            self.length += len(items)
        except ValueError: # the buffer is not big enough
            self.resize((self.length+len(items))*self.BUFFER_EXTEND_SIZE)
            self.extend(items)

    def resize(self, newsize):
        """
        resize the internal buffer
        
        you might want to do this to speed things up if you know you want it
        to be a lot bigger eventually
        """
        if newsize < self.length:
            raise ValueError("accumulator buffer cannot be made smaller that the length of the data")
        self.__buffer.resize(newsize)

    def fitbuffer(self):
        """
        re-sizes the buffer so that it fits the data, rather than having extra space

        """
        self.__buffer.resize(self.length)
        
    ## apparently __getitem__ is deprecated!
    ##  but I'm not sure how to do it "right"    
    def __getitem__(self, index):
        if index > self.length-1:
            raise IndexError("index out of bounds")
        elif index < 0:
            index = self.length-1
        return self.__buffer[index]
    
    def __getslice__(self, i, j):
        """
        a.__getslice__(i, j) <==> a[i:j]
    
        Use of negative indices is not supported.
        
        This returns a COPY, not a view, unlike numpy arrays
        This is required as the data buffer needs to be able to change.
        """
        if j > self.length:
            j = self.length
        return self.__buffer[i:j].copy()

    def __str__(self):
        return self.__buffer[:self.length].__str__()

    def __repr__(self):
        return "Accumulator%s"%self.__buffer[:self.length].__repr__()[5:]
        
