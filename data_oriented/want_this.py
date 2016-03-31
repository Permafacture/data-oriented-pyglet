Components
==========

textured_render_domain = TexturedRenderDomain(texture)
#textured_stationary_polygon_domain = TexturedStationaryPolygonDomain() 
#textured_moving_polygon_domain     = TexturedMovingPolygonDomain()
textured_rotating_polygon_domain   = TexturedRotatingPolygonDomain() 
triangle_strip_polygon = TriangleStripDomain()
sprite_domain = SpriteDomain() #Animated is just sprite with the texture_index updating
integer_counter = LinearCounter()
angle
position
velocity
#acceleration

{
  domain_type1: [ (slice1,fun1),#slice into this domain_type
                  (slice2,fun2),
                 ]
}

Systems
=======

render_update(verts(),tex_coords())

tex_coords[slice0] = tex_coords_from_index(index)
tex_coords[slice1] = tex_coords_from_index(animation_counter())

animation_counter.update()

verts[slice00] = update_localverts_from_pos(local_verts,broadcaster,position)
verts[slice10] = update_localverts_from_posangle(local_verts,broadcaster,position,angle)
verts[slice20] = update_localverts_from_posangle(local_verts,broadcaster,position(velocity),angle)

positions[slice000] = static positions
positions[slice100] = apply_velocity(velocity,position)

Transitions
===========

Many components match up one to one: velocity -> position, counter -> tex_index

Some broadcast up: positions -> verts

Some reduce/filter: ???

Main Loop
=========




#Background items
@Entity(textured_render_domain,triangle_strip_polygon,textured_stationary_polygon_domain,sprite_domain)
class BackgroundEntity(object):

    def add(self,position,width,height,texture_index):
        polygon_coords,tex_coords = sprite_domain.add(width, height, position=position, texture_index=10)
        triangle_strips = triangle_strip_polygon.add(polygon_coords,tex_coords)
        renderer = textured_render_domain.add(triangle_strips)
      
    #def update(self):
    #    pos = position.update()
    #    position_broadcaster = position2coords_broadcaster.update()
    #    polygon_coords, tex_coords = polygon_coords.update(pos[position_broadcaster])
    #    triangle_strips = triangle_strips.update(polygon_coords,tex_coords)
    #    renderer.update(triangle_strips)


#fancy background
@Entity(textured_render_domain,position,angle,animated_domain,integer_counter)
class FancyBackgroundItem(object):

    def add(self,):
        texture_index = integer_counter(begin,start,stop,step,repeat=True)
        polygon_coords,tex_coords = animated_domain.add(width, height, position=position, texture_index=10)
        angle = angle_domain.add(angle)
        polygon_coords,tex_coords = animated_domain.add(width, height, 
            position=position, texture_index=texture_index)
 
        triangle_strips = triangle_strip_polygon.add(polygon_coords,tex_coords)
        renderer = textured_render_domain.add(triangle_strips)

    #def update(self):
    #    texture_index = integer_counter.update()
    #    position 
    #    polygon_coords, tex_coords = polygon_coords.update(pos)
    #    triangle_strips = triangle_strips.update(polygon_coords,tex_coords)
    #    renderer.update(triangle_strips)
     
#baddies
Entity(textured_render_domain, position, angle, collision_domain, animated_domain)


def update_animations(integer_counter,animated_domain):
    animated_domain.texture_index = integer_counter.accumulator

def update_textures(*everything_with_tex_coords, ???):
    for thing in everything_with_tex_coords:
        thing.tex_coords = animated_domain.tex_coords

def update_renderer(*everything_that_renders):
   


'''

Renderer

    internally:
      bound texture
      camera pos

    consumes:
      textured_triangle_strips (verts, tex_coords)
      colored_triangle_strips (verts,coolor_coords)

    exports:
      rendered output in camera reference frame

TexturedTriangleStripRenderer
   
    internally:
      tex_index_to_tex_coords mapping
 
    consumes:
      #wound_verts_in_world_ref_fram
      texture_index

    exports:
      tex_coords

DynamicPolygon

    internally:
      position
      angle
      wound_verts_in_local_ref_frame

    consumes:
      position_incrementer
      angle_incrementer

    exports:
      wound_verts_in_world_ref_frame

AnimatedSprite

    internally:
      hit_box_in_local_ref_frame

    consumes:
      animation_incrementer

    exports:
      hit_box_in_world_coords (depends on poly attrs)
      texture_index

Systems:

  camera_ref_frame = translate(camera pos, global_ref_frame
  global_ref_frame = translate(pos,angle,local_ref_frame)
  pos = decide_position(position_incrementer)
  angle = decide_angle(angle_incrementer)
  tex_coords = tex_coords_from_index(index)
  ???


''' 
