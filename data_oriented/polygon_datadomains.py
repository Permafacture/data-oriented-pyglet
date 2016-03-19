'''
Classes for rendering colored/textured polygons through pyglet

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
#TODO add textured polygons

import numpy as np
from numpy import sin, cos, pi, sqrt
from math import atan2
import pyglet
from pyglet import gl
from collections import namedtuple

from data_oriented import DataDomain, BroadcastingDataDomain, ArrayAttribute

class RenderableColoredTraingleStrips(DataDomain):
    '''Data Domain for rendering colored triangle strips
    
    exposes verts and colors attributes, 
      and renders them as gl.GL_TRIANGLE_STRIP
    
    exposes datatype information that child domains should respect
    '''
    dtype_tuple = namedtuple('Dtype',('np','gl'))
    vert_dtype = dtype_tuple(np.float32,gl.GL_FLOAT)
    color_dtype = dtype_tuple(np.float32,gl.GL_FLOAT)

    def __init__(self):
      super(RenderableColoredTraingleStrips,self).__init__()

      #arrayed data
      self.verts = ArrayAttribute('verts',2,self.vert_dtype.np)
      self.colors = ArrayAttribute('colors',3,self.color_dtype.np)
      self.array_attributes.extend([self.verts,self.colors])

      self.DataAccessor = self.generate_accessor('RenderableAccessor')

    def draw(self):
        gl.glClearColor(0.2, 0.4, 0.5, 1.0)
        gl.glBlendFunc (gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)                             
        gl.glEnable (gl.GL_BLEND)                                                            
        gl.glEnable (gl.GL_LINE_SMOOTH);                                                     
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glEnableClientState(gl.GL_COLOR_ARRAY)

        n = len(self.as_array(self.verts))
        #TODO verts._buffer.ctypes.data is awkward
        gl.glVertexPointer(2, self.vert_dtype.gl, 0, self.verts._buffer.ctypes.data)
        gl.glColorPointer(3,  self.color_dtype.gl, 0, self.colors._buffer.ctypes.data)
        gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, n)

class LinearTimer(DataDomain):
    '''count by an interval in ticks. When min or max value is reached, sets a
    flag.  If `repeating=True`, timer is reset and repeats'''
    #TODO should take a datatype argument
    def __init__(self,repeating=True,dtype=np.float32):
        super(LinearTimer,self).__init__()

        self.repeating = repeating

        #arrayed data
        self.max_value  = ArrayAttribute('max_value',1,dtype) 
        self.min_value  = ArrayAttribute('min_value',1,dtype) 
        self.interval   = ArrayAttribute('interval',1,dtype)
        self.accumulator= ArrayAttribute('accumulator',1,dtype)
        self.ready_flag = ArrayAttribute('ready_flag',1,np.bool)
        self.array_attributes.extend([self.max_value, self.min_value, 
            self.interval, self.accumulator, self.ready_flag])

        self.DataAccessor = self.generate_accessor('LinearTimerAccessor')

    def add(self,interval,max_value,min_value=0):
        kwargs.update({'max_value'  :max_value,
                       'min_value'  :min_value,
                       'interval'   :interval,
                       'accumulator':max_value,
                       'ready_flag' :False,
                       })
        accessor = super(LinearTimer,self).add(**kwargs) 
        return accessor
    

    def update_accumulator(self):
        accumulator = self.as_array(self.accumulator)
        interval = self.as_array(self.interval)
        ready = self.as_array(self.ready_flag)
        max_value = self.as_array(self.max_value)
        min_value = self.as_array(self.min_value)

        accumulator += interval

        underflow = accumulator < min_value #must not be <= 
        ready[underflow] = True
        if self.repeating:
          accumulator[underflow] =  max_value[underflow]

        overflow = accumulator > max_value  #must be >, not >=
        ready[overflow] = True
        if self.repeating:
          accumulator[overflow] =  min_value[overflow]


class WrappingTimer(DataDomain):
    '''set an interval to apply once per tick and the accumulator wraps 
    back around.'''
    #TODO should take a datatype argument

    def __init__(self, dtype=np.float32):
        super(WrappingTimer,self).__init__()

        #arrayed data
        self.max_value  = ArrayAttribute('max_value',1,dtype) 
        self.min_value  = ArrayAttribute('min_value',1,dtype) 
        self.interval   = ArrayAttribute('interval',1,dtype)
        self.accumulator    = ArrayAttribute('accumulator',1,dtype)
        self.array_attributes.extend([self.max_value,self.min_value,
            self.interval,self.accumulator])

        self.DataAccessor = self.generate_accessor('WrappingTimerAccessor')

    def add(self,interval,min_value,max_value,**kwargs):
        kwargs.update({'min_value':min_value,
                       'max_value':max_value,
                       'interval':interval,
                       'accumulator':max_value,
                       })
        accessor = super(WrappingTimer,self).add(**kwargs) 
        return accessor
    

    def update_accumulator(self):
        as_array  = self.as_array
        accumulator   = as_array(self.accumulator)
        interval  = as_array(self.interval)
        max_value = as_array(self.max_value)
        min_value = as_array(self.min_value)
        span = max_value - min_value
        accumulator += interval
        underflow = accumulator <= min_value
        accumulator[underflow] += span[underflow]
        overflow = accumulator >= max_value
        accumulator[overflow] -= span[overflow]
        
class Polygon(DataDomain):
    '''I'm thinking it would be nice to have a class to tie together the 
    vertex generating and color generating data domains as an interface to
    the triangle strip renderer.  But this is just a thought / TODO'''

class RotateablePolygon(BroadcastingDataDomain):
    '''Data Domain for convex polygons to be rendered in pyglet

    registers with RenderableColoredTraingleStrips
    '''

    def __init__(self,renderable_domain):
      super(RotateablePolygon,self).__init__()
      #TODO manage datatypes gracefully...
      v_dtype = renderable_domain.vert_dtype.np
      c_dtype = renderable_domain.color_dtype.np

      #arrayed data
      self.data = ArrayAttribute('data',5,v_dtype)
      #self.color_cache=ArrayAttribute(3,cdtype)  TODO: use ColoredPolygon
      #TODO Don't pass allocator here, use array_attributes list to imply allocator
      #TODO don't put accessors in array_attributes!
      self.render_accessor = self.register_domain(renderable_domain,self.allocator.array_allocator)
      self.array_attributes.extend([self.data,self.render_accessor])

      #TODO is ArrayAttribute essentially the same as register_domain?
      #property data
      self.position = ArrayAttribute('position',2,v_dtype)
      self.angle = ArrayAttribute('angle',1,v_dtype)
      self.color = ArrayAttribute('color',3,c_dtype)
      self.broadcastable_attributes.extend([self.position, self.angle, self.color])

 
      self.DataAccessor = self.generate_accessor('PolygonDataAccessor')

    def add(self,pts,position=(0,0),color=(1,0,0),**kwargs):
      '''add a polygon defined by its pts'''
      #TODO assert shape of pos and color
      data = self.gen_data(pts)
      kwargs.update({'position':position,
                     'color':color,
                     'data':data,
                     'angle':0})
      accessor = super(RotateablePolygon,self).add(**kwargs) 

      return accessor

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

    def update_vertices(self):
        '''Update vertices to render based on positions and angles communicated
        through the data accessors'''
        as_array = self.as_array

        initiald = as_array(self.data)
        angles = as_array(self.angle)
        positions = as_array(self.position)
        indices = as_array(self.indices)

        cos_ts, sin_ts = cos(angles), sin(angles)
        cos_ts -= 1
        #here's a mouthfull.  see contruction of initial_data in init.  sum-difference folrmula applied 
        #and simplified.  work it out on paper if you don't believe me.
        xs, ys, rs, xhelpers, yhelpers = (initiald[:,x] for x in range(5))
        pts = self.render_accessor.verts  #TODO: not user if this means every call below is to as_array...
        #pts = self.render_accessor.verts[:] 
        #  using the setter of the accessor! maybe verts[:]?
        pts[:,0] = xhelpers*cos_ts[indices]
        pts[:,1] = yhelpers*sin_ts[indices]
        pts[:,0] -= pts[:,1]                 
        pts[:,0] *= rs                
        pts[:,0] += xs                
        pts[:,0] += positions[indices,0]

        pts[:,1] = yhelpers*cos_ts[indices]
        tmp = xhelpers*sin_ts[indices]
        pts[:,1] += tmp
        pts[:,1] *= rs
        pts[:,1] += ys
        pts[:,1] += positions[indices,1]

    def update_colors(self):
        toarr = self.as_array
        local_colors = toarr(self.color)[toarr(self.indices)]
        self.render_accessor.colors[:] = local_colors 

    def update(self):
        self.update_vertices()
        self.update_colors()


class RegularPolygonAdder(object):
    '''Shortcut for adding polygons'''

    def __init__(self, domain):
      self.domain = domain

    def polyOfN(self,radius,n):
        '''helper function for making polygons'''
        r=radius
        if n < 3:
            n=3
        da = 2*pi/(n)     #angle between divisions
        return [[r*cos(da*x),r*sin(da*x)] for x in range(int(n))]

    def add(self,radius,number,position,color):
       pts = self.polyOfN(radius,number)
       return self.domain.add(pts,position,color)

