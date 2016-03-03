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
from pyglet.graphics.allocation import Allocator, AllocatorMemoryException

DEFAULT_SIZE = 1

class DefraggingAllocator(Allocator):
    '''Deviates from the design decisions of pyglet.graphics.allocation
    by keeping track of allocated regions and allowing for compaction.

    caller is responsible for giving unique id's to entries.'''

    def __init__(self,capacity=0):
        self._id2selector_dict = {}
        self.dirty = False
        super(DefraggingAllocator,self).__init__(capacity)

    def flush(self):
        '''forget all allocations'''
        self.starts = []
        self.sizes = []
        self.dirty=False
        self._id2selector_dict = {}

    def selector_from_id(self,id):
        start, size = self._id2selector_dict[id]
        if size == 1:
          return start
        else:
          return slice(start,start+size,1)

    def index_from_id(self,id):
        start, size = self._id2selector_dict[id]
        return start

    def slice_from_id(self,id):
        start, size = self._id2selector_dict[id]
        return slice(start,start_size,1)
 
    def all_valid_selector(self):
        return self.starts[-1]+self.sizes[-1]

    def alloc(self,id,size):
        free_start = super(DefraggingAllocator,self).alloc(size)
        self._id2selector_dict[id] = (free_start,size)
        return free_start

    def realloc(self,id,new_size):
        '''Dealloc id and then realloc with a new size'''
        #Deviates from philosophy of original dealloc because compaction makes
        #it unlikely that there will be much free space within the buffer,
        #thus those optimizations are not advantageous.
        #if self._id2selector_dict[id][1] == 0 #probably not an optimization
        self.dealloc(id)
        return self.alloc(id,new_size)

    def dealloc(self,id):
        start, size = self._id2selector_dict.pop(id)
        self.dirty = True
        super(DefraggingAllocator,self).dealloc(start,size)

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
        free_start = 0 #start at the begining
        source_selectors = []
        target_selectors = []
        starts=[]
        sizes = []
        id2selector = self._id2selector_dict
        start_getter = lambda x: x[1][0] #sort by starts
        for id, (start, size) in sorted(id2selector.items(), key=start_getter):
          #TODO, accumulate contiguous source areas
          assert start >= free_start
          if start != free_start:
            source_selectors.append(slice(start,start+size,1))
            start = free_start
            target_selectors.append(slice(start,start+size,1))
            id2selector[id] = (start,size)
            starts.append(start)
            sizes.append(size)
          free_start = start+size

        self.starts = starts
        self.sizes = sizes
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

        self.index_from_id = self.broadcast_allocator.index_from_id
        self.slice_from_id = self.array_allocator.slice_from_id
        self.dirty = self.array_allocator.dirty #Just for consistency

    def iter_selectors(self):
        '''return the id, broadcastable index and array slice for every item
        that is allocated.'''

        #selector_by_id = self.array_allocator.slice_from_id
        selector_by_id = self.array_allocator.slice_from_id
        for id, idx in sorted(self.broadcast_allocator._id2selector_dict.items(),key=lambda x: x[1][0]):
           yield (id,idx[0],selector_by_id(id))

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
        return allocator.starts[-1]+allocator.sizes[-1]

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
