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
from data_oriented.polygon_datadomains import RotateablePolygon, RenderableColoredTraingleStrips



class ColorChangingRotateablePolygon(RotateablePolygon):
    '''add ability to change color from black to self.color'''

    def __init__(self,*args,**kwargs):
        super(ColorChangingRotateablePolygon,self).__init__(*args,**kwargs)
        self.intensity = ArrayAttribute('intensity',1,np.float32)
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

    def update_colors(self):
        as_array = self.as_array
        colors = self.render_accessor.colors
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

        polygon_domain1.update()
        polygon_domain2.update()
        render_domain.draw()
        fps_display.draw()

    pyglet.clock.schedule(lambda _: None)

    pyglet.app.run()

