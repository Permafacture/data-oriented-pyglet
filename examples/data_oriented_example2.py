'''
Second example showing a Data Oriented ORM which registers sub domains 
within other domains, ie: heirarchical data domains

Sub-domains directly update thier region of the parent domain for 
 best performance.

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

#TODO: are `register` and `add` different?

import numpy as np
from numpy import sin, cos, pi, sqrt
from math import atan2
import pyglet
from pyglet import gl
from collections import namedtuple

from data_oriented import DataDomain, ArrayAttribute, BroadcastableAttribute

class RenderableColoredTraingleStrips(DataDomain):
    '''Data Domain for rendering colored triangle strips
    
    sub domains that register with this one must provide the following 
    interface:
  
      how_many() -> returns n = number of vertex/color pairs to render
 
      update(colors, verts) -> take arrays colors and verts and 
        insert n colors and verts into those arrays where n is what
        `how_many` reported. 

      additionally, subdomains should know and respect the vert_dtype
      and color_dtype properties of this domain'''

    dtype_tuple = namedtuple('Dtype',('np','gl'))
    vert_dtype = dtype_tuple(np.float32,gl.GL_FLOAT)
    color_dtype = dtype_tuple(np.float32,gl.GL_FLOAT)

    def __init__(self,size=16):
      super(RenderableColoredTraingleStrips,self).__init__(size=size)
      self._registered_domains = [] #this should be DataDomain functionality

      #arrayed data
      self.verts = ArrayAttribute('verts',size,2,self.vert_dtype.np)
      self.colors = ArrayAttribute('colors',size,3,self.color_dtype.np)
      self.array_attributes.extend([self.verts,self.colors])

      self.DataAccessor = self.generate_accessor('RenderableAccessor')

    def register(self,sub_domain):
        self._registered_domains.append(sub_domain)

    def update(self):
        # flush verts and colors
        self.allocator.starts=[]
        self.allocator.sizes=[]
        for domain in self._registered_domains:
          n = domain.how_many()
          start = self.safe_alloc(n)
          selector = slice(start,start+n,1)
          domain.update(self.colors[selector],self.verts[selector])

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

class RotateablePolygon(DataDomain):
    '''Data Domain for convex polygons to be rendered in pyglet

    registers with RenderableColoredTraingleStrips
    '''

    def __init__(self,renderable_domain,size=16):
      super(RotateablePolygon,self).__init__(size=size)
      renderable_domain.register(self)
      #TODO manage datatypes gracefully...
      v_dtype = renderable_domain.vert_dtype.np
      c_dtype = renderable_domain.color_dtype.np

      #arrayed data
      self.data = ArrayAttribute('data',size,5,v_dtype)
      #self.color_cache=ArrayAttribute(size,3,cdtype)  TODO: use ColoredPolygon
      self.array_attributes.extend([self.data])

      #property data
      self.position = BroadcastableAttribute('position',2,v_dtype)
      self.angle = BroadcastableAttribute('angle',1,v_dtype)
      self.color = BroadcastableAttribute('color',3,c_dtype)

      self.broadcastable_attributes.extend([self.position, self.angle, self.color])
 
      self.DataAccessor = self.generate_accessor('PolygonDataAccessor')


    def how_many(self):
        '''return the length of the region of memory this domain is able
        to update, so that the parent domain can allocate space within its
        arrays and provide direct access to the area of memory this domain
        will be allowed to modify'''
        return self.as_array(self.data).shape[0]

    def add(self,pts,position=(0,0),color=(1,0,0),**kwargs):
      '''add a polygon defined by its pts'''
      #TODO assert shape of pos and color
      data = self.gen_data(pts)
      kwargs.update({'position':position,
                     'color':color,
                     'data':data,
                     'angle':0})
      return super(RotateablePolygon,self).add(**kwargs)

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

    def update(self,colors,verts):
        self.update_vertices(verts)
        self.update_colors(colors)

    def update_vertices(self,verts):
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
       
        pts = verts  #directly accessing arrays to be rendered
       
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

    def update_colors(self,colors):
        local_colors = self.as_array(self.color)
        colors[:] = local_colors #[:] needed to assign data into array

class ColorChangingRotateablePolygon(RotateablePolygon):
    '''add ability to change color from black to self.color'''

    def __init__(self,*args,**kwargs):
        super(ColorChangingRotateablePolygon,self).__init__(*args,**kwargs)
        self.intensity = BroadcastableAttribute('intensity',1,np.float32)
        self.broadcastable_attributes.append(self.intensity)
        self.DataAccessor = self.generate_accessor('ColorChangingPolygonAccessor')

    def add(self,pts,position=(0,0),color=(1,0,0),intensity=1):
      '''add a polygon defined by its pts'''
      #TODO assert shape of pos and color
      data = self.gen_data(pts)
      kwargs = {'position':position,
                'color':color,
                'intensity':intensity, 
                'data':data,
                'angle':0}
      return super(ColorChangingRotateablePolygon,self).add(pts,**kwargs)

    def update_colors(self,colors):
        as_array = self.as_array
        #TODO, again it would be more efficient to work with the raw
        # BroadcastableAttributes first before broadcasting.
        local_colors = as_array(self.color) * as_array(self.intensity)[:,None]
        colors[:] = local_colors

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

if __name__ == '__main__':
    width, height = 640,480
    window = pyglet.window.Window(width=width, height=height, vsync=False)
    fps_display = pyglet.clock.ClockDisplay()
    text = """Data Domain"""
    label = pyglet.text.HTMLLabel(text, x=10, y=height-10)

    render_domain = RenderableColoredTraingleStrips()
    polygon_domain1 = RotateablePolygon(render_domain)
    polygon_domain2 = ColorChangingRotateablePolygon(render_domain)
    poly_adder1 = RegularPolygonAdder(polygon_domain1)
    poly_adder2 = RegularPolygonAdder(polygon_domain2)

    def gen_poly_args(n):
      '''return arguments for creating n regular polygons with randomized
      values through a RegularPolygonAdder'''
      positions = [(x*width,y*height) for x,y in np.random.random((n,2))]
      rs = [r*50 for r in np.random.random(n)] 
      ns = [int(m*10)+3 for m in np.random.random(n)] 
      colors = np.random.random((n,3)).astype(render_domain.color_dtype.np)
      return ((r,m,pos,col) for r,m,pos,col in zip(rs,ns,positions,colors))

    n1=50
    ents1 = [poly_adder1.add(*args) for args in gen_poly_args(n1)]
    n2=50
    ents2 = [poly_adder2.add(*args) for args in gen_poly_args(n2)]

    rates1 = list(np.random.random(n1)*.01)
    rates2 = list(np.random.random(n2)*-.01)

    import types
    def color_changing_ent_to_class(ent,period=1000.):
        '''add an inc_intensity method to an ent so that it starts at a
        random phase and increments the color intensity through a sin wave'''
        start = int(np.random.random()*period)

        def _intensity_generator():
            n=0
            while True:
              yield .5*sin(start+n/period)+.5
              n+=1

        intensity_generator = _intensity_generator()
        ent.intensity_generator = intensity_generator

        def inc_intensity(self):
            self.intensity = intensity_generator.next()
 
        ent.inc_intensity = types.MethodType(inc_intensity,ent)
        return ent

    ents2 = [color_changing_ent_to_class(ent) for ent in ents2]


    @window.event
    def on_draw():
        global angles

        window.clear()
        for i, ent in enumerate(ents1):
          ent.angle+=rates1[i]
        for i, (ent) in enumerate(ents2):
          ent.angle+=rates2[i]
          ent.inc_intensity()

        render_domain.update()
        render_domain.draw()
        fps_display.draw()

    pyglet.clock.schedule(lambda _: None)

    pyglet.app.run()

