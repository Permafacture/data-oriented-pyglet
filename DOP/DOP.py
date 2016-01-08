'''
Data Oriented ORM

TODO: 
  pyglet probably has the domain versioning for a good reason. Figure out
    what exactly and likely implement it here.

  come up with better names for the Attribute types
'''
import numpy as np
from pyglet import gl
from pyglet.graphics import allocation
from math import pi, sin, cos,atan2,sqrt
from collections import namedtuple
from accessors import data_accessor_factory

dtype_tuple = namedtuple('Dtype',('np','gl'))

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

    def __init__(self,size,dim,dtype):
      ''' create a numpy array buffer of shape (size,dim) with dtype==dtype'''
      #TODO: might could alternatively instatiate with an existing numpy array?
      self.dtype=dtype
      self._dim = dim
      self._buffer = np.empty((size,dim),dtype=dtype)*np.NAN

    def __getitem__(self,selector):
      return self._buffer[selector]

    def __setitem__(self,selector,data):
      self._buffer[selector]=data

    def resize(self,count):
      self._buffer.resize((count,self._dim))

class SingleAttribute(object):
    '''holds a resize-able, re-allocateable, buffer
    for data that is one to one relationship with an object.
    TODO: make reallocateable (ie, for deletions)'''

    def __init__(self,name,dtype):
      '''dtype -> numpy data type for array representation
         name -> property name to access from DataOriented Object'''
      self.name = name
      self.dtype=dtype
      self._buffer = list()

    def __getitem__(self,selector):
      return self._buffer[selector]

    def __setitem__(self,selector,data):
      self._buffer[selector]=data

    def add(self,item):
      self._buffer.append(item)
      return len(self._buffer)-1 #return idx

    def as_array(self):
      return np.array(self._buffer,dtype=self.dtype)

    def __repr__(self):
      return self.name

class PolygonDomain(object):
    '''Data Domain for convex polygons to be rendered in pyglet
    TODO: push DOP related code to a DataDomain class and put polygon
    rendering specific code into a subclass'''
    vert_dtype = dtype_tuple(np.float32,gl.GL_FLOAT)
    color_dtype = dtype_tuple(np.float32,gl.GL_FLOAT)

    def __init__(self,size=16):
      self.allocator = allocation.Allocator(size)
      self._id2index_dict = {}
      self._next_id = 0


      self.indices = ArrayAttribute(size,1,np.int32)

      #arrayed data
      self.data = ArrayAttribute(size,5,np.float32)
      self.verts = ArrayAttribute(size,2,self.vert_dtype.np)
      self.colors = ArrayAttribute(size,3,self.color_dtype.np)
      self._array_attributes = [self.indices,self.data,self.verts,self.colors]

      #property data
      self.positions = SingleAttribute('position',np.float32)
      self.angles = SingleAttribute('angle',np.float32)
      self._single_attributes = [self.positions, self.angles]
 
      self.DataAccessor = data_accessor_factory('PolygonDataAccessor',self)

    def _safe_alloc(self, count):
      '''Allocate vertices, resizing the buffers if necessary.'''
      try:
          return self.allocator.alloc(count)
      except allocation.AllocatorMemoryException, e:
          capacity = _nearest_pow2(e.requested_capacity)
          #self._version += 1
          for attribute in self._array_attributes:
              attribute.resize(capacity)
          self.allocator.set_capacity(capacity)
          return self.allocator.alloc(count)

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
        return slice(0,end+1,1)

    def polyOfN(self,radius,n):
        '''helper function for making polygons'''
        r=radius
        if n < 3:
            n=3
        da = 2*pi/(n)     #angle between divisions
        return [[r*cos(da*x),r*sin(da*x)] for x in range(n)]


    def add(self,n,r,position=(0,0),color=(1,0,0)):
      '''add a regular convex polygon with n sides or radius r'''
      #TODO assert shape of pos and color
      pts = self.polyOfN(r,n)
      data = self.gen_data(pts)
      n = len(data) 

      start = self._safe_alloc(n)
      selector = slice(start,start+n,1)
      
      index = self.positions.add(position)
      self.angles.add(0)
      self.indices[selector] = index

      self.data[selector] = data
      self.colors[selector] = color #relies on broadcasting

      id =self._next_id 
      self._id2index_dict[id] = index
      self._next_id += 1

      return self.DataAccessor(self,id)

    def gen_data(self,pts): 
        l = len(pts)
        #wind up the vertices, so we don't have to do it when speed counts.
        #I dont really know which is clock wise and the other counter clock wise, btw
        cw = pts[:l//2]
        ccw = pts[l//2:][::-1]
        flatverts = [None]*(l)
        flatverts[::2]=ccw
        flatverts[1::2]=cw
        wound = [flatverts[0]]+flatverts+[flatverts[-1]]
        #prewound vertices can be transformed without care for winding.
        #Now, store the vertices in a way that can be translated as efficiently as possible later 
        #construct list of (x,y,r, x_helper, y_helper)
        #note that from alpha to theta, x changes by r*[cos(theta+alpha)-cos(alpha)]
        #lets call the initial angle of a vert alpha
        #so later, at theta, we want to remember cos(alpha) and sin(alpha)  
        #they are the helper values
        return [(pt[0],pt[1],sqrt(pt[0]**2+pt[1]**2),
              cos(atan2(pt[1],pt[0])),sin(atan2(pt[1],pt[0]))) for pt in wound]

    def draw(self):
        #get selector
        #generate fresh verts 
        #TODO (Data Oriented Object setters should set a dirty flag)
        #draw arrays
        pass

if __name__ == "__main__":
  polygon_domain = PolygonDomain()
