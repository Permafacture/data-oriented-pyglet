'''
First example showing a Data Oriented ORM with object-instance like 
data accessors

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

import numpy as np
from numpy import sin, cos, pi, sqrt
from math import atan2
import pyglet
from pyglet import gl
from collections import namedtuple
from random import random

from data_oriented import DataDomain, BroadcastingDataDomain, ArrayAttribute

class RenderableColoredTraingleStrips(DataDomain):
    '''Data Domain for rendering colored triangle strips
    
     subdomains should know and respect the vert_dtype
      and color_dtype properties of this domain'''

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
        #TODO: would be more efficient to operate on the BroadcastableAttributes
        # prior to broadcasting.  How to offer this flexibility without
        # complicating the interface?  going with less efficient for now
        angles = as_array(self.angle)
        positions = as_array(self.position)

        cos_ts, sin_ts = cos(angles), sin(angles)
        cos_ts -= 1
        #here's a mouthfull.  see contruction of initial_data in init.  sum-difference folrmula applied 
        #and simplified.  work it out on paper if you don't believe me.
        xs, ys, rs, xhelpers, yhelpers = (initiald[:,x] for x in range(5))
        pts = self.render_accessor.verts  #TODO: ech! every operation below is 
        #pts = self.render_accessor.verts[:] 
        #  using the setter of the accessor! maybe verts[:]?
        pts[:,0] = xhelpers*cos_ts
        pts[:,1] = yhelpers*sin_ts
        pts[:,0] -= pts[:,1]                 
        pts[:,0] *= rs                
        pts[:,0] += xs                
        pts[:,0] += positions[:,0]

        pts[:,1] = yhelpers*cos_ts
        tmp = xhelpers*sin_ts
        pts[:,1] += tmp
        pts[:,1] *= rs
        pts[:,1] += ys
        pts[:,1] += positions[:,1]

    def update_colors(self):
        local_colors = self.as_array(self.color)
        self.render_accessor.colors[:] = local_colors 

    def update(self):
        self.update_vertices()
        self.update_colors()


##
#
# Helper functions for making polygons
#
##

def polyOfN(radius,n):
    '''helper function for making polygons'''
    r=radius
    if n < 3:
        n=3
    da = 2*pi/(n)     #angle between divisions
    return [[r*cos(da*x),r*sin(da*x)] for x in range(n)]

def random_poly(width,height,domain):
    position = (random()*width,random()*height)
    r = random()*50
    n = int(random()*10)+3
    pts = polyOfN(r,n)
    color = (random(),random(),random())
    return domain.add(pts,position,color)



if __name__ == '__main__':
    from random import random
    import time
    #Limit run time for profiling
    run_for = 15 #seconds to run test for
    def done_yet(duration = run_for, start=time.time()):
      return time.time()-start > duration

    width, height = 640,480
    window = pyglet.window.Window(width=width, height=height, vsync=False)
    fps_display = pyglet.clock.ClockDisplay()
    text = """Data Domain"""
    label = pyglet.text.HTMLLabel(text, x=10, y=height-10)

    render_domain = RenderableColoredTraingleStrips()
    polygon_domain1 = RotateablePolygon(render_domain)

    n=15
    ents = [random_poly(width,height,polygon_domain1) for _ in range(n)]

    rates = list(np.random.random(n)*.01)


    @window.event
    def on_draw():
        global angles

        if done_yet():
          pyglet.app.exit()

        window.clear()
        for i, ent in enumerate(ents):
          ent.angle+=rates[i]

        polygon_domain1.update()
        render_domain.draw()
        fps_display.draw()


    def delete(trash):
      print "delete"
      global ents, rates
      ent = ents.pop(5)
      rates.pop(5)
      del ent
    
    pyglet.clock.schedule(lambda _: None)
    pyglet.clock.schedule_interval(delete, 1) 
    pyglet.app.run()
