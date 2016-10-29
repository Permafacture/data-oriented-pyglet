'''
Numpy-ECS example of animated sprites

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
import numpy as np
from numpy import sin, cos, pi, sqrt
#python version compatability
import sys
if sys.version_info < (3,0):
    from future_builtins import zip, map
from math import atan2
import pyglet
from pyglet import gl
from collections import namedtuple
from operator import add

from numpy_ecs.global_allocator import GlobalAllocator
from numpy_ecs.components import DefraggingArrayComponent as Component

#for reproduceable output
seed = 123456789
random.seed(seed)
np.random.seed(seed)


window_width, window_height = 640,480


dtype_tuple  = namedtuple('Dtype',('np','gl'))
vert_dtype   = dtype_tuple(np.float32,gl.GL_FLOAT)
tex_dtype   = dtype_tuple(np.float32,gl.GL_FLOAT)

animator_type = np.dtype([('min_val',    np.int32),
                          ('max_val',    np.int32),
                          ('interval',   np.int32),
                          ('accumulator',np.int32)])


allocator = GlobalAllocator((Component('render_verts' , (3,), vert_dtype.np ),
                             Component('tex_coords'   , (3,), tex_dtype.np  ),
                             Component('poly_verts'   , (5,), vert_dtype.np ),
                             Component('position'     , (3,), vert_dtype.np ),
                             Component('velocity'     , (1,), vert_dtype.np ),
                             Component('animator'     , (1,), animator_type )),

                             allocation_scheme = (
                                                  (1,1,1,1,1,1), 
                                                 )
                           )
def wind_pts(pts,reshape=False):
    '''take clockwise or counter clockwise points and wind them as would
    be needed for rendering as triangle strips'''
    if reshape:
        pts = list(zip(pts[::3],pts[1::3],pts[2::3]))
    l = len(pts)
    cw = pts[:l//2]
    ccw = pts[l//2:][::-1]
    flatverts = [None]*(l)
    flatverts[::2]=ccw
    flatverts[1::2]=cw
    return [flatverts[0]]+flatverts+[flatverts[-1]]

image_name='robin_animation.png'
rows, cols = 5,5
raw = pyglet.image.load(image_name)
raw_seq = pyglet.image.ImageGrid(raw, rows, cols)
items = raw_seq.get_texture_sequence().items[:]
#select animation in order
items = items[20:]+items[15:20]+items[10:15]+items[5:10]+items[0:1]
bird_texture = items[0].texture
animation_lookup = np.array([wind_pts(x.tex_coords,reshape=True) for x in items])

def wind_vertices(pts):
    '''wind pts and pre-compute data that is helpful for transformations'''
    wound = wind_pts(pts) 
    #prewound vertices can be transformed without care for winding.
    #Now, store the vertices in a way that can be translated as efficiently as possible later 
    #construct list of (x,y,r, x_helper, y_helper)
    #note that from alpha to theta, x changes by r*[cos(theta+alpha)-cos(alpha)]
    #lets call the initial angle of a vert alpha
    #so later, at theta, we want to remember cos(alpha) and sin(alpha)  
    #they are the helper values
    return [(pt[0],pt[1],sqrt(pt[0]**2+pt[1]**2),
          cos(atan2(pt[1],pt[0])),sin(atan2(pt[1],pt[0]))) for pt in wound]

def add_sprite(width,height,position,rate,anim_start=0, first_frame=0,
            anim_stop=1, anim_step=1, allocator=allocator):
    width  /= 2.
    height /= 2.
    pts = ( (-width, -height), ( width, -height), 
            ( width,  height), (-width,  height), )

    poly_verts = wind_vertices(pts)

    n = len(poly_verts)
    polygon = {
      'poly_verts': poly_verts,
      'tex_coords': [(0,0,0)]*n,   #allocate empty space. system will fill
      'render_verts': [(0,0,position[2])]*n, 
      'velocity': rate,
      'position': position,
      'animator': (anim_start,anim_stop,anim_step,first_frame) }
    allocator.add(polygon)


def update_position(velocity,position):
    global window_width
    position[:,0] -= velocity
    #wrap around
    position[:,0][position[:,0] < -20] = window_width + 20


def update_animation(tex_coords,animator,animation_lookup=animation_lookup):
    arr = animator
    span = arr['max_val'] - arr['min_val']
    arr['accumulator'] += arr['interval']
    underflow = arr['accumulator'] <= arr['min_val']
    arr['accumulator'][underflow] += span[underflow]
    overflow = arr['accumulator'] >= arr['max_val']
    arr['accumulator'][overflow] -= span[overflow]

    temp = animation_lookup[arr['accumulator']]
    temp.shape = (temp.shape[0]*temp.shape[1],temp.shape[2])
    tex_coords[:] = temp
        

def update_render_verts(render_verts,poly_verts,positions,indices=[]):
    '''Update vertices to render based on positions'''

    render_verts[:,:2] = poly_verts[:,:2] 
    render_verts[:,:2] += positions[:,:2][indices]
    #render_verts[:,2] = positions[indices][:,2]

def update_display(verts,tex_coords,texture=bird_texture):
    gl.glClearColor(0.2, 0.4, 0.5, 1.0)

    gl.glEnable(texture.target)
    gl.glBindTexture(texture.target, texture.id)

    gl.glPushAttrib(gl.GL_COLOR_BUFFER_BIT)
   
    gl.glEnable(gl.GL_ALPHA_TEST)                                                            
    gl.glAlphaFunc (gl.GL_GREATER, .1)                             
    #gl.glEnable(gl.GL_BLEND)                                                            
    #gl.glBlendFunc (gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)                             
    gl.glEnable(gl.GL_DEPTH_TEST) 

    gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
    gl.glEnableClientState(gl.GL_TEXTURE_COORD_ARRAY)

    n=len(verts[:])
    #TODO verts._buffer.ctypes.data is awkward
    gl.glVertexPointer(3, vert_dtype.gl, 0, verts[:].ctypes.data)
    gl.glTexCoordPointer(3, tex_dtype.gl, 0, tex_coords[:].ctypes.data)
    gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, n)
    #unset state
    gl.glPopAttrib()
    gl.glDisable(texture.target)


if __name__ == '__main__':

    window = pyglet.window.Window(window_width, window_height,vsync=False)
    #window = pyglet.window.Window(fullscreen=True,vsync=False)
    #width = window.width
    #height = window.height 
    fps_display = pyglet.clock.ClockDisplay()
    text = """Numpy ECS"""
    label = pyglet.text.HTMLLabel(text, x=10, y = window_height-10)

    n=50

    positions = np.random.random((n,3))
    positions[:,0] *= window_width
    positions[:,1] *= window_height
    sizes = (positions[:,2])*200
    anim_starts = np.random.random_integers(0,20,size=n) 

    for size, position, start in zip(sizes, positions,  anim_starts):
        add_sprite(size,size,position,size*.001,first_frame=start,anim_stop=20)

    allocator._defrag()

    get_sections = allocator.selectors_from_component_query

    def apply_animation(this):
        animation =('tex_coords','animator')
        sections = get_sections(animation)
        update_animation(*(sections[name] for name in animation))

    @window.event
    def on_draw():
        window.clear()

        mover = ('velocity','position',)
        sections = get_sections(mover)
        update_position(*(sections[name] for name in mover))

        render_verts =('render_verts','poly_verts','position')
        broadcast = ('position__to__poly_verts',)
        sections = get_sections(render_verts + broadcast)
        indices = sections.pop(broadcast[0])
        update_render_verts(*(sections[name] for name in render_verts),indices=indices)

        draw =('render_verts','tex_coords')
        sections = get_sections(draw)
        update_display(*(sections[name] for name in draw))

        fps_display.draw()

    pyglet.clock.schedule(lambda _: None)
    pyglet.clock.schedule_interval(apply_animation,.05)

    pyglet.app.run()


