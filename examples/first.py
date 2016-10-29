'''
Example using batches instead of Numpy-ECS

Heavy math happens on each object one at a time.

(object oriented rather than data oriented).

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
from __future__ import absolute_import, division, print_function
#python version compatability
import sys
if sys.version_info < (3,0):
    from future_builtins import zip, map
import numpy as np
import pyglet
from pyglet import gl
from pyglet.graphics import Batch
from math import pi, sin, cos,atan2,sqrt
import time 

#for reproduceable output
seed = 123456789
np.random.seed(seed)

#Limit run time for profiling
run_for = 15 #seconds to run test for
def done_yet(duration = run_for, start=time.time()):
  return time.time()-start > duration

#Set up window
width, height = 640,480
window = pyglet.window.Window(width, height,vsync=False)
#window = pyglet.window.Window(fullscreen=True,vsync=False)
#width = window.width
#height = window.height 
fps_display = pyglet.clock.ClockDisplay()
text = """Unoptimized"""
label = pyglet.text.HTMLLabel(text, x=10, y=height-10)

main_batch = Batch()

def draw():
    global main_batch
    gl.glClearColor(0.2, 0.4, 0.5, 1.0)
    gl.glBlendFunc (gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)                             
    gl.glEnable (gl.GL_BLEND)                                                            
    gl.glEnable (gl.GL_LINE_SMOOTH);                                                     
    gl.glLineWidth (3)

    main_batch.draw()

#helper function for making polygons
def polyOfN(radius,n):
    r=radius
    if n < 3:
        n=3
    da = 2*pi/(n)     #angle between divisions
    return [[r*cos(da*x),r*sin(da*x)] for x in range(n)]


class Convex(object):
    '''Convex polygons for rendering'''
    global main_batch

    def __init__(self,pts, position=None, color=None, radius=0): 
        # comment from chemsed: why the radius argument?
        if position is None:
          position = (width//2, height//2)
        self.position = position
        if color is None:
          color = [60,0,0]
        self.color = color
        self.pts=pts
        self.initializeVertices()

    def initializeVertices(self):
        pts = self.pts
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
        self.initial_data = [(pt[0],pt[1],sqrt(pt[0]**2+pt[1]**2),cos(atan2(pt[1],pt[0])),sin(atan2(pt[1],pt[0]))) for pt in wound]
        verts = self.rotate(0)
        self.n=len(verts)//2
        self.set_colors()
        self.vertlist = main_batch.add(self.n, gl.GL_TRIANGLE_STRIP,None,
  ('v2i,',verts),('c3b',self.colors))

    def set_colors(self):
        self.colors = self.color*self.n

    def rotate(self,theta):
        px, py = self.position
        initiald = self.initial_data
        cost, sint = cos(theta), sin(theta)
        #here's a mouthfull.  see contruction of initial_data in init.  sum-difference folrmula applied 
        #and simplified.  work it out on paper if you don't believe me.
        pts = [(px+x+r*(xhelper*(cost-1)-sint*yhelper),py+y+r*(yhelper*(cost-1)+sint*xhelper)) for x,y,r,xhelper,yhelper in initiald]
        #flatten and return as a tuple for vertbuffer
        return tuple(map(int,[val for subl in pts for val in subl]))
        
    def rotate_and_render(self,angle):
        self.vertlist.vertices = self.rotate(angle)

    def update_colors(self):
        ##print(self.vertlist.colors)
        self.vertlist.colors=self.colors


n=1000
positions = [(x*width,y*height) for x,y in np.random.random((n,2))]
poly_args = [(r*50,int(m*10)+3) for r,m in np.random.random((n,2))] 
colors = [list(map(lambda x: int(x*255),vals)) for vals in np.random.random((n,3))]
ents = [Convex(polyOfN(*pargs),position=pos, color=col) for pargs,pos,col in zip(poly_args,positions,colors)]
angles= [0]*n
rates = list(np.random.random(n)*.02)
@window.event
def on_draw():
    global angle

    if done_yet():
      pyglet.app.exit()

    window.clear()
    for i, ent in enumerate(ents):
      angles[i]+=rates[i]
      ent.rotate_and_render(angles[i])
    draw()
    fps_display.draw()


#pyglet.clock.set_fps_limit(60)
pyglet.clock.schedule(lambda _: None)

pyglet.app.run()
