'''
First example using rough data orientation

Although the same object oriented style is used for generating the data,
it is aggregated together so that heavy maths can be applied en masse.

This sloppy data aggregation comes at the price of being able to access
individual shapes post creation.  IE, all polygons have the same number 
of sides and turn at the same rate.

This file is part of Numpy-ECS.
Copyright (C) 2016 Elliot Hallmark (permafacture@gmail.com)

Numpy-ECS Python is free software: you can redistribute it and/or modify
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
from math import pi, sin, cos,atan2,sqrt
import time 
from collections import namedtuple
from functools import reduce

#for reproduceable output
seed = 123456789
np.random.seed(seed)

#Keep datatypes between numpy and gl consistent
dtype_tuple = namedtuple('Dtype',('np_type','gl_type'))
vert_dtype = dtype_tuple(np.float32,gl.GL_FLOAT)
color_dtype = dtype_tuple(np.float32,gl.GL_FLOAT)

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
text = """Optimized DOP"""
label = pyglet.text.HTMLLabel(text, x=10, y=height-10)


def draw(verts,colors):
    '''draw the numpy arrays `verts` and `colors`.'''

    gl.glClearColor(0.2, 0.4, 0.5, 1.0)
    gl.glBlendFunc (gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)                             
    gl.glEnable (gl.GL_BLEND)                                                            
    gl.glEnable (gl.GL_LINE_SMOOTH);                                                     
    gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
    gl.glEnableClientState(gl.GL_COLOR_ARRAY)

    gl.glVertexPointer(2, vert_dtype.gl_type, 0, verts.ctypes.data)
    gl.glColorPointer(3,  color_dtype.gl_type, 0, colors.ctypes.data)
    gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, len(verts)//2)
    fps_display.draw()

#helper hunction for making polygons
def polyOfN(radius,n):
    r=radius
    if n < 3:
        n=3
    da = 2*pi/(n)     #angle between divisions
    return [[r*cos(da*x),r*sin(da*x)] for x in range(n)]


class Convex(object):
    '''Convex polygons for rendering'''
    def __init__(self,pts, position=None, color=None, radius=0):
        if position is None:
          position = (width//2, height//2)
        self.position = position
        if color is None:
          color = [60,0,0]
        self.color = tuple(color)
        self.pts=pts
        self.initializeVertices()

    def initializeVertices(self):
        px,py = self.position
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
        self.initial_data = [(px,py,pt[0],pt[1],sqrt(pt[0]**2+pt[1]**2),
              cos(atan2(pt[1],pt[0])),sin(atan2(pt[1],pt[0]))) for pt in wound]
        self.n = len(self.initial_data)        
        self.set_colors()

    def set_colors(self):
        self.colors = self.color*self.n
 



## Create shapes
n=150
size = 5 #number of sides
positions = [(x*width,y*height) for x,y in np.random.random((n,2))]
poly_args = [(r*50,size) for r,m in np.random.random((n,2))] 
colors = np.random.random((n,3)).astype(color_dtype.np_type)

ents = [Convex(polyOfN(*pargs),position=pos, color=col) for pargs,pos,col in zip(poly_args,positions,colors)]


#Create Data Oriented Arrays
helpers = []
colors = []
for ent in ents:
  helpers.extend(ent.initial_data)
  colors.extend(ent.colors)

helpers = np.array(helpers)
colors = np.array(colors,dtype=color_dtype.np_type)

def mass_rotate(initial_data,theta):
    initiald = initial_data
    cost, sint = cos(theta), sin(theta)
    #here's a mouthfull.  see contruction of initial_data in init.  sum-difference folrmula applied 
    #and simplified.  work it out on paper if you don't believe me.
    pxs, pys, xs, ys, rs, xhelpers, yhelpers = (initiald[:,x] for x in range(7))
   
    pts = np.empty((len(pxs),2),dtype=vert_dtype.np_type)

    pts[:,0] = xhelpers*(cost-1)  
    pts[:,1] = yhelpers*sint      
    pts[:,0] -= pts[:,1]                 
    pts[:,0] *= rs                
    pts[:,0] += xs                
    pts[:,0] += pxs       

    pts[:,1] = yhelpers*(cost-1)
    tmp = xhelpers*sint
    pts[:,1] += tmp
    pts[:,1] *= rs
    pts[:,1] += ys
    pts[:,1] += pys

    #flatten and return as correct type
    pts.shape = ( reduce(lambda xx,yy: xx*yy, pts.shape), )
    return pts.astype(vert_dtype.np_type)


#instatiate verts array
verts = mass_rotate(helpers,0)

#global state for polygon rotations
angle = 0
rate = .002

@window.event
def on_draw():
    global angle,verts,colors

    if done_yet():
      pyglet.app.exit()

    window.clear()
    angle+=rate
    verts[:] = mass_rotate(helpers,angle)
    draw(verts,colors)
  


#pyglet.clock.set_fps_limit(60)
pyglet.clock.schedule(lambda _: None)

pyglet.app.run()
