'''
Allocation of space in data oriented buffers.



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

DEFAULT_SIZE = 1

class AllocatorMemoryException(Exception):
    '''The buffer is not large enough to fulfil an allocation.

    Raised by `Allocator` methods when the operation failed due to lack of
    buffer space.  The buffer should be increased to at least
    requested_capacity and then the operation retried (guaranteed to
    pass second time).
    
    this exception was taken from pyglet.graphics.allocation
    '''

    def __init__(self, requested_capacity):
        self.requested_capacity = requested_capacity


class DefraggingAllocator(object):
    '''Deviates from the design decisions of pyglet.graphics.allocation
    by keeping track of allocated regions and allowing for compaction.

    caller is responsible for giving unique id's to entries.'''

    def __init__(self,capacity=0):
        self._id2selector_dict = {}
        self._zero_sized = []
        self.dirty = False
        self.capacity=capacity

    def set_capacity(self, size):
        '''Resize the maximum buffer size.
        
        The capaity cannot be reduced.
        '''
        assert size > self.capacity
        self.capacity = size


    def flush(self):
        '''forget all allocations'''
        self.dirty=False
        self._id2selector_dict = {}
        self._zero_sized = []

    def selector_from_id(self,id):
        start, size = self._id2selector_dict[id]
        #from tests, index vs slice access is very performance impacting
        #  this is a worthwile optimization
        if size == 1:
          return start
        else:
          return slice(start,start+size,1)

    def size_from_id(self,id):
        id2sel = self._id2selector_dict
        if id in id2sel:
           start, size = id2sel[id]
           return size
        elif id in self._zero_sized:
           return 0
        else:
           raise ValueError("id %s not allocated" % id)

    def all_valid_selector(self):
        #TODO is it worth making this more efficient?
        a = sorted(self._id2selector_dict.values()) #sorts by value[0] = start
        if a:
          return a[-1][0]+a[-1][1]  #add last start and last size
        else:
          return 0 #TODO ? what should this return??

    def alloc(self,id,size):
        '''allocate space in the buffer. Raises an AllocatorMemoryException if
        request to alloc cannot be fufilled with current capacity.


        This will not fragment the buffer.
        '''
        assert id not in self._id2selector_dict,"alloc'ing an id that is already alloc'd"
        assert id not in self._zero_sized, "alloc'ing an id that is already alloc'd"
        assert size >= 0, "alloc size must be >= 0"
       

        #TODO, really should use pyglet.allocator behaviour and try to alloc
        #  within an empty space since realloc dealloca and then allocs again
        if size == 0:
          self._zero_sized.append(id)
        elif size > 0:
          free_start = self.all_valid_selector()  #+1
          new_size = free_start + size
          if new_size > self.capacity:
             raise AllocatorMemoryException(new_size)
          #else
          self._id2selector_dict[id] = (free_start,size)
          return free_start

    def dealloc(self,id):
        if id in self._id2selector_dict:
          start, size = self._id2selector_dict.pop(id)
          self.dirty = True
        elif id in self._zero_sized:
          self._zero_sized.remove(id)

    #def realloc(self,id,new_size):
    #    '''Dealloc id and then realloc with a new size'''
    #    #Deviates from philosophy of original dealloc because compaction makes
    #    #it unlikely that there will be much free space within the buffer,
    #    #thus those optimizations are not advantageous.
    #    #if self._id2selector_dict[id][1] == 0 #probably not an optimization
    #    self.dealloc(id)
    #    print "allocator realloc:",id,new_size
    #    return self.alloc(id,new_size)


    #def get_allocated_regions(self):
    #    #should give same result as base Allocator, but just wanted to
    #    #implement it according to the paradigm of this class
    #    return tuple(zip(*sorted(self._id2selector_dict.values())))

    def defrag(self):
        '''compact items down to fill any free space created by dealloc's
        returns (source_selectors,target_selectors) where selectors are
        slice objects that can be used to move data in real arrays to the 
        defragmented form.  ex:

            for source_sel, target_sel in zip(defrag_allocator.defrag())
                arr[target_sel] = arr[source_sel]
        '''
        #print "defrag"
        free_start = 0 #start at the begining
        source_selectors = []
        target_selectors = []
        id2selector = self._id2selector_dict
        start_getter = lambda x: x[1][0] #sort by starts
        for id, (start, size) in sorted(id2selector.items(), key=start_getter):
          #TODO, accumulate contiguous source areas
          assert start >= free_start
          if start == 0 or start != free_start:
            source_selectors.append(slice(start,start+size,1))
            start = free_start
            target_selectors.append(slice(start,start+size,1))
            id2selector[id] = (start,size)
          free_start = start+size

        self.dirty = False
        return source_selectors, target_selectors

class ArrayAndBroadcastableAllocator(object):
    '''Bundles allocators for buffers where adding a item adds one to the
    broadcastable buffers and a group to the array allocators: ie the
    ArrayAttributes and BroadcastableAttributes from datadomain'''
    def __init__(self):
        self.array_allocator = DefraggingAllocator(0)
        self.broadcast_allocator = DefraggingAllocator(0)
        self.array_selector = self.array_allocator.all_valid_selector
        self.broadcast_allocator.all_valid_selector

        self.dirty = self.array_allocator.dirty #Just for consistency

    def iter_selectors(self):
        '''return the id, broadcastable index and array slice for every item
        that is allocated.'''

        #selector_by_id = self.array_allocator.slice_from_id
        selector_by_id = self.array_allocator.selector_from_id
        for id, idx in sorted(self.broadcast_allocator._id2selector_dict.items(),key=lambda x: x[1][0]):
           size = idx[1]
           if size == 1:
             #always this. TODO get rid of if 
             yield (idx[0],selector_by_id(id))
           else:
             yield (slice(idx[0],idx[0]+size,1),selector_by_id(id))

    def flush(self):
        self.array_allocator.flush()
        self.broadcast_allocator.flush()
        self.dirty = self.array_allocator.dirty

    def alloc_array(self,id,size):
        '''allocate size for the ArrayAttributes 
        returns array_start'''
        array_start = self.array_allocator.alloc(id,size)
        return array_start

    def last_valid_index(self):
        #TODO This isn;t well named since its for arrays. HAck to get things working now
        allocator = self.array_allocator
        return allocator.all_valid_selector()

    def set_array_capacity(self,capacity):
        self.array_allocator.set_capacity(capacity)

    def alloc_broadcastable(self,id,size=1):
        '''allocate size for the BroadcastableAttributes
        returns first free index'''
        index = self.broadcast_allocator.alloc(id,size)
        return index

    def set_broadcastable_capacity(self,capacity):
        self.broadcast_allocator.set_capacity(capacity)

    def realloc(self,*args):
        raise NotImplementedError

    def dealloc(self,id):
        self.array_allocator.dealloc(id)
        self.broadcast_allocator.dealloc(id)
        self.dirty=True

    def defrag(self):
        '''defrag both ArrayAttributes and BroadcastableAttributes.
        returns (array_fixers, broadcast_fixers) where the fixers are the
        lists of pairs of slices documented in DefraggingAllocator.defrag'''
        array_fixers = self.array_allocator.defrag()
        broadcast_fixers = self.broadcast_allocator.defrag()
        self.dirty = False
        return (array_fixers, broadcast_fixers)
