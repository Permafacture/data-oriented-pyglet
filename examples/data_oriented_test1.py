'''
Example showing a Data Oriented ORM which registers sub domains 
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

    n1=150
    ents1 = [random_poly(width,height,polygon_domain1) for _ in range(n1)]

    rates1 = list(np.random.random(n1)*.01)


    @window.event
    def on_draw():
        global angles

        if done_yet():
          pyglet.app.exit()

        window.clear()
        for i, ent in enumerate(ents1):
          ent.angle+=rates1[i]

        polygon_domain1.update()
        render_domain.draw()
        fps_display.draw()

    pyglet.clock.schedule(lambda _: None)

    pyglet.app.run()

