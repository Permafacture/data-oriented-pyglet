colored_render_domain = ColoredRenderDomain()
textured_render_domain = TexturedRenderDomain(texture)
collision_domain = CollisionDomain()
hit_box = HitBoxDomain()
triangle_strip_polygon = TriangleStripDomain()
position = PositionDomain()
angle = AngleDomain()
color = ColorDomain()
position2coords_broadcaster = BroadcastDomain(position, coords)
sprite_domain = SpriteDomain()
animated_domain = AnimatedSpriteDomain()


#Background items
Entity(textured_render_domain,triangle_strip_polygon,position,sprite_domain)

    def add(self):
      position = positiondomain.add(pos)
      sprite_domain.add(width, height, position=position, texture_index=10)
      triangle_strip_polygon.add
      
      


#fancy background
Entity(textured_render_domain,position,angle,animated_domain)

#baddies
Entity(textured_render_domain, position, angle, collision_domain, animated_domain)

