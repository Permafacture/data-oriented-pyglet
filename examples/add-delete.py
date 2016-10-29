'''
Numpy-ECS example of adding and deleting entitiess

Hard coded example of the following Entity_class_id table:
 
  entity_class_id, vertices,  color,   positions, rotator, 

          1110,      1,         1,         1,         0,  
          1111,      1,         1,         1,         1,  

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
from numpy import sin, cos, pi, sqrt
from math import atan2
import random
import pyglet
from pyglet import gl
from collections import namedtuple
from operator import add
#import pdb

from numpy_ecs.global_allocator import GlobalAllocator
from numpy_ecs.components import DefraggingArrayComponent as Component

seed = 123456789
random.seed(seed)
np.random.seed(seed)

dtype_tuple  = namedtuple('Dtype',('np','gl'))
vert_dtype   = dtype_tuple(np.float32,gl.GL_FLOAT)
color_dtype  = dtype_tuple(np.float32,gl.GL_FLOAT)

counter_type = np.dtype([('max_val',  np.float32),
                        ('min_val',    np.float32),
                        ('interval',   np.float32),
                        ('accumulator',np.float32)])


allocator = GlobalAllocator((Component('render_verts' , (3,), vert_dtype.np ),
                             Component('poly_verts'   , (5,), color_dtype.np),
                             Component('color'        , (3,), color_dtype.np),
                             Component('position'     , (3,), vert_dtype.np ),
                             Component('rotator'      , (1,), counter_type  )),

                             allocation_scheme = (
                                                  (1,0,1,1,0), 
                                                  (1,1,1,1,1), 
                                                 )
                           )
def polyOfN(n,radius):
    '''helper function for making polygons'''
    r=radius
    if n < 3:
        n=3
    da = 2*pi/(n)     #angle between divisions
    return [[r*cos(da*x),r*sin(da*x)] for x in range(int(n))]

def wind_vertices(pts): 
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

def add_rotating_regular_polygon(n_sides,radius,position,rate,
                                   color=(.5,.5,.5),allocator=allocator):
    rot_max = 4*np.pi
    rot_min = -rot_max
    pts = polyOfN(n_sides,radius)
    poly_verts = wind_vertices(pts)
    n = len(poly_verts)
    polygon = {
      'poly_verts': poly_verts,
      'render_verts': [(0,0,position[2])]*n,
      'color':[color]*n,
      'position':position,
      'rotator':(rot_max,rot_min,rate,0) }
    allocator.add(polygon)

def add_regular_polygon(n_sides,radius,position,
                          color=(.5,.5,.5),allocator=allocator):
    pts = polyOfN(n_sides,radius)
    poly_verts = wind_vertices(pts)
    n = len(poly_verts)
    polygon = {
      'render_verts': [(x+position[0],y+position[1],position[2]) for x,y,_,_,_ in poly_verts],
      'color':[color]*n,
      'position':position,}
    allocator.add(polygon)

def update_rotator(rotator):
        arr=rotator
        span = arr['max_val'] - arr['min_val']
        arr['accumulator'] += arr['interval']
        underflow = arr['accumulator'] <= arr['min_val']
        arr['accumulator'][underflow] += span[underflow]
        overflow = arr['accumulator'] >= arr['max_val']
        arr['accumulator'][overflow] -= span[overflow]


def update_render_verts(render_verts,poly_verts,positions,rotator,indices=[]):
    '''Update vertices to render based on positions and angles communicated
    through the data accessors'''

    angles = rotator['accumulator']

    cos_ts, sin_ts = cos(angles), sin(angles)
    cos_ts -= 1
    #here's a mouthfull.  see contruction of initial_data in init.  sum-difference folrmula applied 
    #and simplified.  work it out on paper if you don't believe me.
    xs, ys, rs, xhelpers, yhelpers = (poly_verts[:,x] for x in range(5))
    pts = render_verts  
    #print 'shapes:',angles.shape
    pts[:,0] = xhelpers*cos_ts[indices]
    pts[:,1] = yhelpers*sin_ts[indices]
    #IndexError: array used as indices= must be integer type. Sometime the  
    # function runs with empty parameters as indices =[]
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

def update_display(render_verts,colors):
    #print("display called")
    gl.glClearColor(0.2, 0.4, 0.5, 1.0)
    gl.glBlendFunc (gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)                             
    gl.glEnable (gl.GL_BLEND)                                                            
    gl.glEnable (gl.GL_LINE_SMOOTH);                                                     
    gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
    gl.glEnableClientState(gl.GL_COLOR_ARRAY)

    n = len(render_verts[:])
    #TODO verts._buffer.ctypes.data is awkward
    gl.glVertexPointer(3, vert_dtype.gl, 0, render_verts[:].ctypes.data)
    gl.glColorPointer(3,  color_dtype.gl, 0, colors[:].ctypes.data)
    gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, n)


def add_some(n,n2=None,allocator=allocator):
    #pdb.set_trace()
    '''add n random polygons to allocator

    There's two types of polygons. if only n is given, will distribute randomly.
    if n2 is given, distibute n to one type and n2 to the other
    '''

    assert isinstance(n,int) and (1 if n2 is None else isinstance(n2,int)),\
        "n1 and n2 (if given) must be integers"

    if n2 is None:
      a = random.random()
      n1 = int(n*a)
      n2 = n-n1
    else: 
      n1 = n
      n2 = 0 #chemsed comment: it doesn't seem to work as intended

    positions = [(x*width,y*height,z) for x,y,z in np.random.random((n1,3))]
    rs = [r*50 for r in np.random.random(n1)] 
    ns = [int(m*10)+3 for m in np.random.random(n1)] 
    colors = np.random.random((n1,3)).astype(color_dtype.np)
    rates = np.random.random(n1)*.01

    for n,r, position, color, rate in zip(ns,rs, positions, colors, rates):
      add_rotating_regular_polygon(n,r,position,rate,color)
    #from before indicies could be calculated
    #indices = np.array(reduce(add, [[x,]*7 for x in range(n1)], []),dtype=np.int)

    positions = [(x*width,y*height,z) for x,y,z in np.random.random((n2,3))]
    rs = [r*50 for r in np.random.random(n2)] 
    ns = [int(m*10)+3 for m in np.random.random(n2)] 
    colors = np.random.random((n2,3)).astype(color_dtype.np)

    for n_sides,radius, position, color in zip(ns,rs, positions, colors):
      add_regular_polygon(n_sides,radius,position,color)



def delete_some(n,allocator=allocator):
    #pdb.set_trace()
    guids = random.sample(allocator.guids,n) 
    #Value Error: sample (102,101) larger than population (4)
    #Something is wrong with the guids and _next_guid method in global_allocator.py
    # I noticed that deleting an element in tuple leave them to "None" at the index
    for guid in guids:
        allocator.delete(guid)



if __name__ == '__main__':
    #pdb.set_trace()
    width, height = 640,480
    window = pyglet.window.Window(width, height,vsync=False)
    #window = pyglet.window.Window(fullscreen=True,vsync=False)
    #width = window.width
    #height = window.height 
    fps_display = pyglet.clock.ClockDisplay()
    text = """Numpy ECS"""
    label = pyglet.text.HTMLLabel(text, x=10, y=height-10)
   
    #add some polygons 
    add_some(100,50)
    allocator._defrag()

    get_sections = allocator.selectors_from_component_query

   
    @window.event
    def on_draw():
        #print("draw called")
        window.clear()

        allocator._defrag()

        rotator = ('rotator',)
        sections = get_sections(rotator)
        update_rotator(*(sections[name] for name in rotator))

        render_verts =('render_verts','poly_verts','position','rotator')
        broadcast = ('position__to__poly_verts',)
        sections = get_sections(render_verts + broadcast)
        indices = sections.pop(broadcast[0])

        update_render_verts(*(sections[name] for name in render_verts),indices=indices)

        draw =('render_verts','color')
        sections = get_sections(draw)
        update_display(*(sections[name] for name in draw))

        fps_display.draw()

    pyglet.clock.schedule(lambda _: None)
    #pdb.set_trace()
    pyglet.clock.schedule_interval(lambda x,*y: add_some(*y),1,2)
    #pdb.set_trace()
    pyglet.clock.schedule_interval(lambda x,*y: delete_some(*y),2,4)
    pyglet.app.run()
