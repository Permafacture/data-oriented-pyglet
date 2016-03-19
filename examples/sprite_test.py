import pyglet
from pyglet import gl
from collections import namedtuple
import numpy as np
from numpy import sin, cos, pi, sqrt
from math import atan2
from time import time

from data_oriented import DataDomain, BroadcastingDataDomain, ArrayAttribute



# Create and open a window

width, height = 500,500
window = pyglet.window.Window(width, height,vsync=False)
fps_display = pyglet.clock.ClockDisplay()

#def animation_generator(image_name,rows,cols,total_frames=None):
#    raw = pyglet.image.load(image_name)
#    raw_seq = pyglet.image.ImageGrid(raw, rows, cols)
#    if total_frames is None:
#      total_frames = rows*cols
#    else:
#      assert total_frames <= rows*cols
#
#    items = raw_seq.get_texture_sequence().items[:]
#    yield items[0].texture #need to export the texture for binding
#    temp_array = np.array(items[0].tex_coords,dtype=vert_dtype.np)
#    images = items[20:]+items[15:20]+items[10:15]+items[5:10]+items[0:1]
#    while True:
#      for image in images[::-1]:
#        temp_array[:] = image.tex_coords
#        print "yielded",temp_array
#        yield temp_array



class RenderableTexturedTraingleStrips(DataDomain):
    '''Data Domain for rendering textured triangle strips
    
    '''
    dtype_tuple = namedtuple('Dtype',('np','gl'))
    vert_dtype = dtype_tuple(np.float32,gl.GL_FLOAT)
    tex_dtype = dtype_tuple(np.float32,gl.GL_FLOAT)

    def __init__(self,texture):
      super(RenderableTexturedTraingleStrips,self).__init__()

      self.texture = texture

      #arrayed data
      self.verts = ArrayAttribute('verts',3,self.vert_dtype.np)
      self.tex_coords = ArrayAttribute('tex_coords',3,self.tex_dtype.np)
      self.array_attributes.extend([self.verts,self.tex_coords])

      self.DataAccessor = self.generate_accessor('RenderableAccessor')

    def draw(self):
      v_dtype = self.vert_dtype
      t_dtype = self.tex_dtype
      verts = self.as_array(self.verts)
      tex_coords = self.as_array(self.tex_coords)
      gl.glClearColor(0.2, 0.4, 0.5, 1.0)

      gl.glEnable(texture.target)
      gl.glBindTexture(texture.target, texture.id)

      gl.glPushAttrib(gl.GL_COLOR_BUFFER_BIT)
      
      gl.glEnable (gl.GL_BLEND)                                                            
      gl.glBlendFunc (gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)                             

      gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
      gl.glEnableClientState(gl.GL_TEXTURE_COORD_ARRAY)

      n=len(verts)
      #TODO verts._buffer.ctypes.data is awkward
      gl.glVertexPointer(3, v_dtype.gl, 0, verts.ctypes.data)
      gl.glTexCoordPointer(3, t_dtype.gl, 0, tex_coords.ctypes.data)
      gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, n)
      #unset state
      gl.glPopAttrib()
      gl.glDisable(texture.target)

class Sprite(BroadcastingDataDomain):
    '''Data Domain for textured rectangles to be rendered in pyglet

    registers with RenderableColoredTraingleStrips
    '''
    #TODO add a layer attribute. set pts[:,2] to it

    def __init__(self,renderable_domain,tex_coords_array):
      super(Sprite,self).__init__()

      v_dtype = renderable_domain.vert_dtype.np
      self.tex_coords_array = tex_coords_array

      #arrayed data
      self.data = ArrayAttribute('data',5,v_dtype)
      self.render_accessor = self.register_domain(renderable_domain,self.allocator.array_allocator)
      self.array_attributes.extend([self.data,self.render_accessor])

      #property data
      self.layer = ArrayAttribute('layer',1,v_dtype)
      self.position = ArrayAttribute('position',2,v_dtype)
      self.angle = ArrayAttribute('angle',1,v_dtype)
      self.texture_index = ArrayAttribute('texture_index',1,np.int16) 
      self.broadcastable_attributes.extend([self.layer,self.position, self.angle, self.texture_index])

 
      self.DataAccessor = self.generate_accessor('SpriteDataAccessor')

    def add(self,width, height, position=(100,100), texture_index=10, 
              layer=0,**kwargs):
      '''add a sprite, defined by it's width and height'''
      #TODO assert shape of pos and color
      width  /= 2.
      height /= 2.
      pts = ( (-width, -height), ( width, -height), 
              ( width,  height), (-width,  height), )

      data = self.gen_data(pts)
      kwargs.update({'position':position,
                     'texture_index':texture_index,
                     'data':data,
                     'layer':layer,
                     'angle':0})
      accessor = super(Sprite,self).add(**kwargs) 

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
        
        pts[:,2]=as_array(self.layer)[indices]   #tex coords are 3D

    def update_textures(self):
        temp = self.tex_coords_array[self.as_array(self.texture_index)]
        temp.shape = (temp.shape[0]*temp.shape[1],temp.shape[2])
        self.render_accessor.tex_coords = temp

    #def update(self):
    #    self.update_vertices()
    #    self.update_textures()

def wind_pts(pts):
    '''wind vertices that were defined in CW or CCW order for rendering'''
    pts = zip(pts[::3],pts[1::3],pts[2::3])
    l = len(pts)
    #wind up the vertices, so we don't have to do it when speed counts.
    #I dont really know which is clock wise and the other counter clock wise, btw
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
texture = items[0].texture
tex_coords_array = np.array([wind_pts(x.tex_coords) for x in items])

render_domain = RenderableTexturedTraingleStrips(texture)
sprite_domain = Sprite(render_domain,tex_coords_array)

n=100

texture_indices = np.random.random_integers(5,24,n)
positions = np.random.random((n,2))
positions[:,0] *= width
positions[:,1] *= height
layers = np.random.random(n)
sizes = layers + .2 
sizes *= 150
#TODO, can't get layers working
layers = 1 - layers
s_max = np.max(sizes)
s_min = np.min(sizes)


ents = [sprite_domain.add(s,s,position=p,texture_index=i,
           layer=-l) for s,p,i,l in zip(sizes,positions,
           texture_indices,layers)]

sprite_domain.update_textures()

@window.event
def on_draw():
  global next_time,tex_coords
  window.clear()
  sprite_domain.update_vertices()
  render_domain.draw()
  fps_display.draw()

if __name__ == '__main__':

  pyglet.clock.schedule(lambda _: None)

  pyglet.app.run()

