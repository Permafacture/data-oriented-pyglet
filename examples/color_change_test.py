'''
Second example showing a Data Oriented ORM which registers sub domains 
within other domains, ie: heirarchical data domains

Sub-domains directly update thier region of the parent domain for 
 best performance.

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

from data_oriented import ArrayAttribute
from data_oriented.polygon_datadomains import RotateablePolygon, RenderableColoredTraingleStrips, RepeatingTimer, WrappingTimer



class ColorChangingRotateablePolygon(RotateablePolygon):
    '''add ability to change color from black to self.color'''

    def __init__(self,rotation_domain,timer_domain,*args,**kwargs):
        super(ColorChangingRotateablePolygon,self).__init__(*args,**kwargs)
        self.rotation_accessor = self.register_domain(rotation_domain,self.allocator.broadcast_allocator)
        self.timer_accessor = self.register_domain(timer_domain,self.allocator.broadcast_allocator)
        self.broadcastable_attributes.extend((self.rotation_accessor,self.timer_accessor))
        self.DataAccessor = self.generate_accessor('ColorChangingPolygonAccessor')

    def add(self,pts,position=(0,0),color=(1,0,0),interval=.0001,rate=.01):
      '''add a polygon defined by its pts'''
      #TODO assert shape of pos and color
      data = self.gen_data(pts)
      kwargs = {'position':position,
                'color':color,
                'data':data,
                'angle':0}
      accessor = super(ColorChangingRotateablePolygon,self).add(pts,**kwargs)
      index = self.allocator.broadcast_allocator.selector_from_id(accessor._id)
      timer = self.timer_accessor
      rotator = self.rotation_accessor
      try:
        timer.interval[index]    = interval
        timer.max_value[index]   = 1
        rotator.max_value[index] = 4*np.pi
        rotator.min_value[index] = -4*np.pi
        rotator.interval[index]  = rate
      except TypeError:
        #TODO
        #So, adding the first one, interval is a np.float.  Every time after
        #it is an array as expected. Probably caused by having a zero sized array
        timer.interval    = interval
        timer.max_value   = 1
        rotator.max_value = 4*np.pi
        rotator.min_value = -4*np.pi
        rotator.interval  = rate
     
      return accessor

    def update_vertices(self):
        as_array = self.as_array
        #TODO. weird, writes into as_array(self.angle)[:] don't work (nothing happens)
        # AH! it's because as array gives a temporary array that has been 
        # broadcast with indices. That might get confusing!
        as_array(self.angle)[:] = self.rotation_accessor.counter
        super(ColorChangingRotateablePolygon,self).update_vertices()

    def update_colors(self):
        as_array = self.as_array
        colors = self.render_accessor.colors
        intensities = self.timer_accessor.counter
        #TODO, again it would be more efficient to work with the raw
        # BroadcastableAttributes first before broadcasting.
        local_colors = as_array(self.color) * intensities[:,None]
        colors[:] = local_colors[as_array(self.indices)]

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

    def add(self,radius,number,position,color,interval=.0001,rate=.01):
       pts = self.polyOfN(radius,number)
       return self.domain.add(pts,position,color,interval,rate)

if __name__ == '__main__':
    width, height = 640,480
    window = pyglet.window.Window(width=width, height=height, vsync=False)
    fps_display = pyglet.clock.ClockDisplay()
    text = """Data Domain"""
    label = pyglet.text.HTMLLabel(text, x=10, y=height-10)

    render_domain = RenderableColoredTraingleStrips()
    timer_domain = RepeatingTimer() 
    rotation_domain = WrappingTimer()

    #polygon_domain1 = RotateablePolygon(render_domain)
    polygon_domain2 = ColorChangingRotateablePolygon(rotation_domain,timer_domain,render_domain)

    #poly_adder1 = RegularPolygonAdder(polygon_domain1)
    poly_adder2 = RegularPolygonAdder(polygon_domain2)

    def gen_poly_args(n):
      '''return arguments for creating n regular polygons with randomized
      values through a RegularPolygonAdder'''
      positions = [(x*width,y*height) for x,y in np.random.random((n,2))]
      rs = [r*50 for r in np.random.random(n)] 
      ns = [int(m*10)+3 for m in np.random.random(n)] 
      colors = np.random.random((n,3)).astype(render_domain.color_dtype.np)
      rates = np.random.random(n2)*-.01
      intensities = np.random.random(n)/2000 +.0001
      return ((r,m,pos,col,i,rate) for r,m,pos,col,i,rate in zip(rs,ns,positions,colors,intensities,rates))

    #n1=50
    #ents1 = [poly_adder1.add(*args) for args in gen_poly_args(n1)]
    n2=150
    ents2 = [poly_adder2.add(*args) for args in gen_poly_args(n2)]

    @window.event
    def on_draw():
        global angles

        window.clear()
        #for i, ent in enumerate(ents1):
        #  ent.angle+=rates1[i]
        #for i, (ent) in enumerate(ents2):
        #  ent.angle+=rates2[i]
          #ent.inc_intensity()

        #polygon_domain1.update()
        timer_domain.update_counter()
        rotation_domain.update_counter()
        polygon_domain2.update()
        render_domain.draw()
        fps_display.draw()

    pyglet.clock.schedule(lambda _: None)

    pyglet.app.run()

