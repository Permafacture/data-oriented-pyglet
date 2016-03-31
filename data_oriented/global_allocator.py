'''
Allocating Entity values in contiguous Component arrays, providing Systems
with access to simple slices of components.
'''

# Systems require slices, not index arrays or multiple slices, to access data
# in components.  Naively allocating spaces in arrays without regard for this 
# will not work. For instance:
# 
# [
# 
#   entity_class_id, vertices, animated, positions, velocity
# 
#               01,         1,        0,         0,        0
#               02,         1,        0,         1,        0
#               03,         1,        0,         1,        1
#               04,         1,        1,         0,        0
#               05,         1,        1,         1,        0
#               06,         1,        1,         1,        1
# 
# ]
# 
# Trying to apply update_verts(positions, velocities), one cannot get a single
# slice on positions.  This table can be re-arranged to work:
# 
# [
# 
#   entity_class_id, vertices, animated, positions, velocity
# 
#               01,         1,        0,         0,        0
#               02,         1,        0,         1,        0
#               03,         1,        0,         1,        1
#               06,         1,        1,         1,        1
#               05,         1,        1,         1,        0
#               04,         1,        1,         0,        0
# ]
# 
# Now velocities can update a single slice of positions, and postions can
# update a single slice of vertices (including those that are also animated).
#   I THINK! I could be wrong. Please let me know.
#
# If the entity_class_id is a binary representation of the components it 
# requires, then given an addition of any arbitrary collection of 
# attributes, we can determine what entity_class it belongs to and add
# the values to sections of the array that maintain ideal contiguity.
#
# [
# 
#   entity_class_id, vertices, animated, positions, velocity
# 
#             1000,         1,        0,         0,        0
#             1010,         1,        0,         1,        0
#             1011,         1,        0,         1,        1
#             1111,         1,        1,         1,        1
#             1110,         1,        1,         1,        0
#             1100,         1,        1,         0,        0
# ]
#
#

#Old Notes
#
#    entity_class_id, render_verts, texture_coords, collision_verts, positions, velocity, animated_texture
#  
#                01,             1,              1,               0,         0,        0,                0                
#                02,             1,              1,               0,         1,        0,                0
#                03,             1,              1,               0,         1,        1,                0
#                04,             1,              1,               1,         0,        0,                0
#                05,             1,              1,               1,         1,        0,                0
#                06,             1,              1,               1,         1,        1,                0
#                07,             1,              1,               0,         0,        0,                1                
#                08,             1,              1,               0,         1,        0,                1
#                09,             1,              1,               0,         1,        1,                1
#                10,             1,              1,               1,         0,        0,                1
#                11,             1,              1,               1,         1,        0,                1
#                12,             1,              1,               1,         1,        1,                1
#
#original:
#
#01: 110000                
#02: 110100
#03: 110110
#04: 111000
#05: 111100
#06: 111110
#07: 110001                
#08: 110101
#09: 110111
#10: 111001
#11: 111101
#12: 111111
#
#
#sorted:
#
#01: 110000                
#02: 110100
#03: 110110
#04: 111000
#05: 111100
#06: 111110
#12: 111111
#11: 111101
#09: 110111
#07: 110001                
#10: 111001


#def gray_code(high_val,bits=None):
#    '''return a list of Gray code encoded strings that has at least high_val 
#       entries. Binary Gray codes are powers of two, so len(gray_code) will
#       be the next power of two >= to high_val.
#    '''
#    bits = bits or ['0','1']
#
#    bits  = [bit+'0' for bit in bits] + [bit+'1' for bit in bits[::-1]]
#    if len(bits) >= high_val:
#        return '0b'+bits
#    return gray_code(high_val,bits)
#
#
#
#
#def component_dict_to_graycode(comp_dict,names):
#    assert all(key in names for key in comp_dict.keys())
#    bin_string = ''.join('1' if name in comp_dict else '0' for name in names)
#    return int(bin_string,base=2)
from table import Table, TableRow
        
def defrag_single_component(component,base_of_section,guids,sizes):

    target_selectors = []
    source_selector = []

    free_start = base_of_section
    current = free_start
    for guid, size in zip(guids,sizes):
        if guid is None:
          current += size
        else:
          source_selectors.append(slice(current,   size,1))
          target_selectors.append(slice(free_start,size,1))
          free_start += size
          current    += size
    for source, target in zip(source_selectors, target_selectors):
        component[target] = component[source]


def print_allocation_table(names,allocation_table):
    '''pretty representation of allocation table'''
    row_format = "{:>15}"*len(allocation_table[0])
    print row_format.format(*names)
    for row in allocation_table:
       print row_format.format(*row)

def verify_component_schema(allocation_schema):
    '''given an allocation schema as a list of lists, return True if the schema
    keeps all Component arrays contiguous.  Else return False'''
    started = [False] * len(allocation_schema[0])
    ended   = [False] * len(allocation_schema[0])
    for row in allocation_schema:
        for i,val in enumerate(row):
            if val: 
               if not started[i]:
                  started[i] = True
               else: 
                  if ended[i]:
                    return False
            elif started[i]:
              ended[i] = True
    return True


            
def slices_from_entity_mask(mask,allocation_scheme,allocation_table,names):
    '''mask is an integer that is a binary mask on the entity_class, selecting
    certain Components.  ie mask = 3 accepts (1,0,1,1) but not (1,0,1,0).

    returns a dictionary of {'component name': slice(relevant section)}
    '''

    tuple_add = lambda t1,t2: tuple(x+y for x,y in zip(t1,t2))
    starts = tuple(0 for x in range(len(allocation_table[0])))
    ends   = tuple(1 for x in range(len(allocation_table[0])))

    #starts will be the index to all the beginings of sections of Components
    # ends will be the last index of component + 1 for slice.
    found = False
    for row_mask,row in zip(allocation_scheme,allocation_table):
       ends = tuple_add(row,ends)
       if mask & row_mask == mask: #row contains all components in question
         if not found:
            found = True
       else:
         if found:
           #result = {}
           #slices = tuple(slice(s,e,None) for s,e in zip(starts,ends))
           #return {names[-i-1]:slices[-i-1] for i,exists in enumerate(bin(mask)[2:][::-1]) if int(exists)}
           break
       if not found: starts = tuple_add(starts,row)
    if found:
      slices = tuple((slice(s,e,None) for s,e in zip(starts,ends)))
      return {names[-i-1]:slices[-i-1] for i,exists in enumerate(bin(mask)[2:][::-1]) if int(exists)}
    else:
      raise ValueError("Mask had no matches")



class GlobalAllocator(object):
    '''Decides how data is added or removed from Components, allocating and 
    deallocting Entities/guids.  Components better be allocated by only one
    of these.

    see comments at top of file for details'''

    def __init__(self,components,allocation_scheme):
        self.component_dict = {component.name:component for component in components}
        names = tuple(comp.name for comp in components) 
        
        self._allocation_table = Table(names)
        for ent_id in (self.entity_class_from_tuple(t) for t in allocation_scheme):
          self._allocation_table.add_key(ent_id)
 
        self._guid_table = Table(names)
        self._cached_deletes = set()
        self._cached_adds = dict()
        self._next_guid = 0
   

    @property
    def next_guid(self):
        self._next_guid += 1
        return self._next_guid

    def _class_id_from_guid(guid):
        #assumes entity has non-zero size for every component that 
        #  defines it's class.  This is the definition of a class_id and is
        #  a result of how add works
        row = row_for_guid(guid)
        return int(''.join(x!=0 for x in row),base=2)

    def entity_class_from_tuple(self,component_tuple):
        '''takes a component tuple like (5,5,0,2,2,2)

        returns the integer that is this entity class'''
        return sum(map(lambda (i,x): 0 if x ==0 else (x/x)*2**i, 
            enumerate(component_tuple[::-1])))

    #def allocation_schema_from_truth_table(self,truth_table):
    #    '''
    #    an allocation schema may be defined as a list of lists.
    #   
    #    convert that to a list of integers where (0,0,1,1) -> 3, etc'''
    #    return map(self.entity_class_from_tuple,truth_table)

    def entity_class_from_dict(self,component_dict):
        '''takes a component dict like {'comp_name1':value}

        returns the integer that is this entity class'''
        names = self._allocation_table.column_names
        for name in component_dict.keys():
          assert name in names, "%s is not a known component name"% (name,)
        entity_tuple = tuple(0 if (component_dict.get(name,None) is None) \
            else 1 for name in names)
        return self.entity_class_from_tuple(entity_tuple)

    def add(self,values_dict):
        alloc_table = self._allocation_table
        names = alloc_table.column_names
        component_dict = self.component_dict
        entity_class_id = self.entity_class_from_dict(values_dict)
        assert entity_class_id in alloc_table.keys(),\
            "may only add collections of components defined in schema"

        def convert_to_component_array(component,value):
            '''converts value to a numpy array with appropriate shape for 
            component'''
            value = np.array(value,dtype = component.datatype)
            assert value.shape[1:] == component._dim,\
                "value must be same dimensions as component"
            return value

        result = {}
        for name, value in values_dict.items():
           result[name] = convert_to_component_array(component_dict[name],value)
        self._cached_adds.setdefault(entity_class_id,list()).append(result)

    def delete(self,guid):
        #update cached_delete set
        pass

    def _defrag(self):
       alloc_table = self._allocation_table
       component_dict  = self.component_dict
       adds_dict  = self._cached_adds
       #delete_set = self._cached_deletes
       def safe_len(item):
           if item is None:
               return 0
           try:
               return(len(item))
           except TypeError:
               #like an integer
               return 1

       #create an empty table like alloc_table
       change_table = Table(alloc_table.column_names)
       for id in alloc_table.keys():
           change_table.add_key(id)

       #fill change table with size changes
       #for guid in delete_set:
       #    entity_class = entity_class_from_guid(guid)
       #    guid_row     = get_guid_row(guid)
       #    change_table[entity_class] -= guid_row
       for entity_class, adds in self._cached_adds.items():
           to_print = entity_class == 7
           if to_print: print "adds:",adds
           for add in adds:
               add = tuple(safe_len(add.get(name,None)) \
                         for name in alloc_table.column_names)
               if to_print: print "add:",add
               change_table[entity_class] += add
       #assert that component has that space
       for name, deltas in zip(change_table.column_names,change_table.columns):
           delta = sum(deltas)
           if delta > 0:
               component_dict[name].alloc(delta)

       #apply deletes
       #for row in self._guid_table:
       #    if row[0] in delete_set:
       #        #mark as removed by changing guid to None
       #        row[0] = None

       #Could I just generate a list of sources and targets that defrags
       # and pushes good data back? Then I need to keep track of insert 
       # positions for adds
       #Need to manage both allocation table and guid allocation table here
       #TODO make i, name, old_sizes, new_sizes using fancy zip stuff
       for name, old_sizes, push_sizes in zip(alloc_table.column_names,
               alloc_table.columns, change_table.columns):
           print "working on %s"%name
           component = component_dict[name]
           section_free_start = old_sizes[0] #the index to the top of this section
           for entity_class, section_size, size_change in zip(alloc_table.keys(),
                   old_sizes,push_sizes):
               #defrag_single_component(component,start)
               #?targets, sources = compact_section(start, stop, guid_table)
               #?defrag_component(component,targets, sources)
               #    compress section
               #resize section
               if size_change:
                 component.push_from_index(section_free_start,size_change)
               #apply adds
               section_pointer = section_free_start #-delete_size
               print "ent class",entity_class
               for add in self._cached_adds.get(entity_class,()):
                   add = add.get(name,None) #add for this component
                   if add is not None:
                       #allocator.add already verified that the set of values
                       # added was complete for this entity class. so no check 
                       # here
                       print "adding",add,"at",section_pointer
                       shape = add.shape or (1,)
                       size = shape[0]
                       component[section_pointer:section_pointer+size] = add
                       section_pointer += size
               section_free_start += section_pointer #top of expanded section
       #set or reset attributes 
       self._cached_adds = dict()
       self._cached_deletes = set()
       for ent_class_id in alloc_table.keys():
           alloc_table[ent_class_id] += change_table[ent_class_id]
       #remove all Nones from guid table

    def selectors_from_class_index(self,class_id):
        alloc_table = self._allocation_table
        n = alloc_table.size[1]
        index = self.class_ids.index(class_id)
        begin = [sum(alloc_table[x,:index])   for x in range(n)]
        end   = [sum(alloc_table[x,:index+1]) for x in range(n)]
        return tuple(slice(b,e,1) for b,e in zip(being, end))

    def safe_alloc(self,class_id,size_dict):
        #TODO would be more efficient if it tries ro alloc in empty space

        if class_id in self.list_class_ids(): 
            raise ValueError('class_id %s already allocated'%class_id)

        component_dict = self.component_dict
        for component_name, size in size_dict.items():
            component_dict[component_name].alloc(size)

        #All component sizes not given are None
        size_dict['class_id'] = class_id
        self._allocation_table.append(size_dict)

    def safe_dealloc(self,class_id):
        for row in self._allocation_table:
            if row['class_id'] == class_id:
                row['class_id'] = None
                break

    def safe_realloc(self,class_id,new_sizes):
        alloc_table = self._allocation_table

        try:
          index, old_selectors = next(((i,row) for i,row in enumerate(alloc_table) if row['class_id'])) 
        except StopIteration:
          raise ValueError('realloc_error: class_id %s was not already allocated'%class_id)

        class_id = old_selectors.pop('class_id')
        def all_smaller(new,old):
            all(new[name]<old.get(name,0) for name in new.keys())

        old_sizes = {name:size_of(selector) for name, 
            selector in old_selectors.items()}

        if all_smaller(new_sizes,old_sizes):
            row[i] = dict(new_sizes)
            row[i]['class_id'] = class_id
            #TODO insert 'None' after this to indicate empty space
            return

        ##else 
        safe_dealloc(class_id)
        safe_alloc(class_id,new_sizes)
        new_selectors = self.selectors_from_class_id(class_id)

        #fill new area with as much of old data as will fit (if it shrank),
        # or leave unallocated space at end if it grew
        components = self.component_dict
        for component_name, old_selector in old_selectors.items():
            new_selector = new_selectors.get(component_name,None)
            if new_selector is not None:
              if size_of(new_selector) >= size_of(old_selector):
                new_selector = slice(new_selector.start,size_of(old_selector),1)
              else:
                old_selector = slice(old_selector.start,size_of(new_selector),1)
              components[component_name].realloc(old_selector,new_selector)


class EntityClassAllocator(object):

    def __init__(self,global_allocator,component_names):
        self.global_allocator = global_allocator
        self.component_names = component_names
        self._allocation_table = []


    

#########
#
#  Components
#
#########



if __name__ == '__main__':
    from components import DefraggingArrayComponent as Component
    import numpy as np

    d1 = Component('component_1',(1,),np.int32)
    d2 = Component('component_2',(1,),np.int32)
    d3 = Component('component_3',(1,),np.int32)
    allocation_scheme = (
      (1,1,1),
      (1,0,1),
      (1,0,0),)

    allocator = GlobalAllocator([d1,d2,d3],allocation_scheme)

    to_add1 = {'component_1':1,'component_3':3,'component_2':2,}
    to_add2 = {'component_1':3,'component_3':3,}
    allocator.add(to_add1)
    allocator.add(to_add2)
    allocator._defrag()
    print allocator._allocation_table
    to_add1 = {'component_1':6,'component_3':8,'component_2':7,}
    to_add2 = {'component_1':2,'component_3':2,}
    allocator.add(to_add1)
    allocator.add(to_add2)
    allocator._defrag() 
    print allocator._allocation_table

