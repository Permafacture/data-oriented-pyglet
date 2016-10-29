'''
Classes to facilitate allocating guids in groups of class_ids

Keeps sizes of allocated areas in a table

class_id  guid  component_1 component_2 ...
   -----
   |       001            7           1
   |       003            6           1
  11...    004            4           1
   |       005            6           1
   |       007            5           1
   -----
   |       008            4           0
  10...    010            6           0
   |       011            2           0
   -----

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
from collections import MutableMapping, Sequence
from types import GeneratorType

INDEX_SEPERATOR = '__to__' # 'ie: index from component1__to__component2

#TODO make row a numpy array and delete TableRow
class TableRow(Sequence):
    '''A tuple that can be added to another tuple of the same size'''
    def __init__(self,*values):
        if isinstance(values[0],GeneratorType):
          self.values = tuple(values[0])
        elif isinstance(values[0],tuple):
          self.values = values[0]
        else:
          self.values = tuple(values)

    def __add__(self,other):
        other = tuple(other)
        assert len(other) == len(self.values), "Must add item of same length"
        return TableRow(this+that for this,that in zip(self.values,other))

    def __sub__(self,other):
        other = tuple(other)
        assert len(other) == len(self.values), "Must add item of same length"
        return TableRow(this-that for this,that in zip(self.values,other))

    def __eq__(self,other):
        return self.values == other

    def __ne__(self,other):
        return self.values != other

    def __repr__(self):
        return "TableRow: %s" %(self.values,)

    def __len__(self):
        return len(self.values)

    def __iter__(self):
        return iter(self.values)

    def copy(self):
        return TableRow(*self.values)

    def __getitem__(self,index):
        return self.values[index]

def slice_is_not_empty(s):
    #print "  ",s.start,s.stop-s.start
    return s.start != s.stop

class Table(object):
    '''An allocation table that has column names (component names) and major 
    rows (class ids) and minor rows (guids).  The minor rows are divisions of 
    the major rows.  Class ids are a tuple which are the binary of
    what columns are present in the guid row.

    keeps track of sizes and starts of allocated guids, and provides 
    functionality for adding and deleting guids, as well as giving the slices
    at which the values of guids can be found in a Component arrays and for
    defragging those arrays.
    '''
    def __init__(self,column_names,class_ids):
        '''column names is a tuple of strings that define, in order, the names
        of the columns present in this table.  class_ids is a tuple of tuples
        that determines the order of the major rows (essential for keeping 
        related arrays contiguous with respect to each other)'''
        self.__col_names = tuple(column_names)
        self.__row_length = len(column_names)
        self.__row_format = ''.join((" | {:>%s}"%(len(name)) for name in column_names))
        self._staged_adds = dict()
        self.known_class_ids = tuple(class_ids)
        self.class_ids = list()
        self.guids = list()
        self.starts = list()
        self.sizes = list()

    @property
    def column_names(self):
        return self.__col_names

    #@property
    #def guid_columns(self):
    #    return zip(*self.sizes)

    #@property
    #def class_id_columns(self):
    #    return zip(*self.as_class_id_table())

    def entity_class_from_tuple(self,sizes_tuple):
        '''takes a component tuple like (5,5,0,2,2,2)

        returns a normalized tuple that is a class id, like (1,1,0,1,1,1)'''
        assert len(sizes_tuple) == self.__row_length, "too many values"
        # Used to convert to integer, but that's unnecessary
        #return sum(map(lambda (i,x): 0 if x ==0 else (x/x)*2**i, 
        #    enumerate(sizes_tuple[::-1])))
        return tuple(0 if x==0 else x/x for x in sizes_tuple)

    #def entity_class_from_dict(self,dictionary):
    #    '''Creates a class id from a dictionary keyed by column_names'''
    #    cols = self.column_names
    #    keys = set(dictionary.keys())
    #    #TODO make this one assert, not a loop
    #    for name in keys:
    #      assert(name in cols),"unknown class_id %s"%(name,)
    #    return tuple(1 if name in keys else 0 for name in cols)

    #    assert len(sizes_tuple) == self.__row_length, "too many values"
    #    # Used to convert to integer, but that's unnecessary
    #    #return sum(map(lambda (i,x): 0 if x ==0 else (x/x)*2**i, 
    #    #    enumerate(sizes_tuple[::-1])))
    #    return tuple(0 if x==0 else x/x for x in sizes_tuple)

    def stage_add(self,guid,value_tuple):
        assert guid not in self.guids, "guid must be unique"
        assert guid not in {t[0] for lst in self._staged_adds.values() \
            for t in lst}, "cannot restage a staged guid"
        ent_class = self.entity_class_from_tuple(value_tuple)
        assert ent_class in self.known_class_ids, \
            "added entity must corispond to a class id in the allocation schema"
        #print "guid %s is class %s"%(guid,ent_class)
        self._staged_adds.setdefault(ent_class,
            list()).append((guid,value_tuple))

    def stage_delete(self,guid):
        '''mark guid None so it can be removed later'''
        self.guids[self.guids.index(guid)] = None

    def make_starts_table(self):
        '''Create a list of tuples where each value is the start index of that
        element. (Table is the sizes)'''
        start = TableRow(*(0,)*self.__row_length)
        table = [start]
        for row in self.sizes:
          start = row + start
          table.append(start)
        return table

    #def class_sizes_table(self):
    #    '''return a list of rows where each row is the size of the class_id's 
    #    in this table.  This can be zipped with class_ids.'''
    #    result = []
    #    empty_row = lambda : TableRow(*(0,)*self.__row_length)
    #    row = empty_row()
    #    known_ids = iter(self.known_class_ids)
    #    this_id = next(known_ids)
    #    for class_id, size_row in zip(self.class_ids,self.sizes):
    #        while class_id != this_id:
    #            result.append(row)
    #            row = empty_row()
    #            this_id = next(known_ids)
    #        row+= size_row
    #    result.append(row)
    #    #if class_ids is exausted but not all known ids were reached, 
    #    #  add empty rows
    #    for empty in known_ids:
    #        result.append(empty_row())
    #    return result

    def section_slices(self):
        #TODO doc string is wrong
        #TODO change to use class_size_table
        '''return a list of slices that represent the portions of each column
        that corrispond to the known class ids in order.  For known ids not 
        present in class_ids, a zero sized slice is used'''
        known_ids = self.known_class_ids
        id_column = self.class_ids
        expressed_ids = filter(lambda x: x in id_column,known_ids)
        starts = list(map(id_column.index,expressed_ids))
        assert all(starts[x]<starts[x+1] for x in range(len(starts)-1)),\
            'id_column must be in same order as known_ids'
        stops = starts[1:]+[None]
        ret_val = {class_id:slice(start,stop,1) for class_id,start,stop in \
            zip(expressed_ids,starts,stops)}
        return ret_val
 
    def rows_from_class_ids(self,class_ids):
        '''
        container::class_ids - must be contiguous

        returns ((start,), (row1,row2, ...)) - tuple of starts of section and
            then all the rows within the section
        '''
        result = []
        starts  = TableRow(*(0,)*self.__row_length) 
        started = self.class_ids[0] in class_ids
        all_ids = iter(self.class_ids)
        for class_id, size_row in zip(all_ids,self.sizes):
             if started == True:
                 if class_id in class_ids:
                     result.append(size_row)
                 else:
                   break
             else:
                 if class_id in class_ids:
                     result.append(size_row)
                     started = True
                 else:
                   starts = starts+size_row
        assert not any(_id in class_ids for _id in all_ids), \
            "given set of class_ids must be contigious"

        return starts,result

    def mask_slices(self, col_names, indices):
        '''
        (string,)::col_names - to use as a mask.
        (string,)::indices - form of  S+INDEX_SEPERATOR+T. S broadcasting to T
          (sizes in S must *always* be 1)

        returns {name1:slice1, ..., index1:index_array1,...}.

        enforces that columns are contiguous.'''

        names = self.__col_names

        def to_indices(string, c_names = names, 
                    sep = INDEX_SEPERATOR):
            p1,p2 = string.split(sep)
            assert (p1 in c_names), '%s must be a column_name'%p1
            assert (p2 in c_names), '%s must be a column_name'%p2
            return c_names.index(p1), c_names.index(p2)

        mask_tuple = tuple(1 if n in col_names else 0 for n in names)
        def in_mask(item_tuple,mask=mask_tuple):
            return (x for x,m in zip(item_tuple,mask) if m)

        known_ids = self.known_class_ids #ordered for contiguity
        matched_ids = {class_id for class_id in known_ids if all(in_mask(class_id))}
        idxs = tuple(map(to_indices,indices))

        sizes  = TableRow(*(0,)*self.__row_length)
        idx_result = tuple(list() for x in range(len(idxs)))

        starts,rows = self.rows_from_class_ids(matched_ids)
        for i,row in enumerate(rows):
            sizes += row 
            for lst, (s,t) in zip (idx_result, idxs):
                assert row[s] == 1, 'must broadcast from size == 1'
                lst.extend([i]*row[t])

        selectors = {n:slice(st,st+si) for n, st, si in zip(names,starts,sizes)\
                    if n in col_names}
        indices = {n:lst for n,lst in zip(indices,idx_result)}
        return selectors,indices

    #def build_index(self,mask,index2single, index2multi):
    #    '''return a list of indices to broadcast an array of single values
    #    to an array of more values.  index2single is the index in the mask of
    #    the column that will only have ones, and index2multi is the index in
    #    the mask of the column that has many values.'''
    #    idx = 0
    #    result = []
    #    for class_id, row in zip(self.class_ids, self.rows):
    #         if started == True:
    #             if class_id in matched_ids:
    #                 assert row[index2single] == 1, "must be single valued"
    #                 result.extend([idx]*row[index2multi])
    #             else:
    #               break
    #         else:
    #             if class_id in matched_ids:
    #                 started = True
    #    return result


    def compress(self,):
        #don't insert into, just replace
        #print "COMPRESS"
        sizes = self.sizes
        class_ids = self.class_ids
        guids = self.guids
        new_class_ids = []
        new_guids = []
        new_sizes = []
 
        empty_row = lambda: TableRow(*(0,)*self.__row_length)
 
        # start at 0 for everything
        sources = []
        targets = []
        free_start = empty_row()
        current_start = empty_row()
        total_alloc = empty_row()
        #TODO could this be reduce?
        ends = TableRow(sum(column) for column in zip(*sizes)) or empty_row() 
        new_ends = ends.copy()

        #TODO section_slices should return [(class_id, section_slice),...]
        section_dict = self.section_slices()
        for class_id in self.known_class_ids:
            #empty slice will have no effect. essentially, skip this loop that
            # iterates over the slice.
            allocs  = empty_row()        
            deallocs  = empty_row()        
            section_slice = section_dict.get(class_id,slice(0,0,1))
            #print "doing class id:",class_id, section_slice
            for guid, size_tuple in zip(guids[section_slice], sizes[section_slice]):
                assert all((start >= free_start for start,
                       free_start in zip(current_start,free_start))),\
                       "next start must be larger than current free start"
                if guid is None:
                    current_start += size_tuple
                    deallocs += size_tuple
                else:
                    #shift data back to cover deletes
                    #print "  counting %s of %s"%(guid,class_id)
                    new_class_ids.append(class_id)
                    new_guids.append(guid)
                    new_sizes.append(size_tuple)
                    if current_start != free_start:
                        #print "size_tuple:\n",size_tuple
                        sources.append(tuple(slice(start,start+size,1) for start,
                                      size in zip(current_start,size_tuple)))
                        targets.append(tuple(slice(start,start+size,1) for start,
                                      size in zip(free_start,size_tuple)))
                        #print "  small alloc for guid",guid,"to",targets[-1]
                    free_start += size_tuple
                    current_start += size_tuple
            #deal with adds
            for added_guid, size_tuple in self._staged_adds.get(class_id,()):
                size = TableRow(size_tuple)
                allocs += size
                #print"  adding guid %s as %s"%(added_guid,class_id)
                new_class_ids.append(class_id)
                new_guids.append(added_guid)
                new_sizes.append(size)
            #free_start = current_start + allocs #TODO part of last debugging
            free_start += allocs
            new_ends += allocs
            new_ends -= deallocs
            #after inserting adds, write the big change to sources and targets
            #Note: empty slices are added here, and are filtered out when we 
            # columnize the row data
            if current_start != free_start:
                source = tuple(slice(start,end,1) for start,end in zip(
                              current_start,ends)) 
                target = tuple(slice(start,end,1) for start,end in zip(
                              free_start,new_ends))
                #print "adding:\n",source,target
                sources.append(source)
                targets.append(target)
                #print "big alloc for class",class_id
                #for s,t in zip(source,target): print s,"-->",t
            #print "starts:\n  %s| %s\n  %s| %s\n" % (current_start, ends, free_start,new_ends)
            #print "starts: %s | %s" % (current_start - free_start, ends - new_ends)
            current_start = free_start.copy() #TODO part of last debugging
            ends = new_ends.copy()
            total_alloc += allocs
            this_class_id = class_id

        self.class_ids = new_class_ids
        self.guids = new_guids
        self.sizes = new_sizes
        self.starts = self.make_starts_table()
        self._staged_adds = {} 

        #columnize the row data
        #TODO make this a generator?
        ret = []
        for new_capacity, col_sources, col_targets in zip(
                new_ends, list(zip(*sources)), list(zip(*targets))):
            #print "sources:"
            col_sources = tuple((s for s in col_sources if slice_is_not_empty(s)))
            #print "targets:"
            col_targets = tuple((t for t in col_targets if slice_is_not_empty(t)))
            #Assert that the above did what we expect
            if __debug__ == True:
                for s,t in zip(col_sources,col_targets):
                    assert s.stop-s.start == t.stop-t.start, \
                        'source size and target size must match'
            assert len(col_sources) == len(col_targets)
            ret.append((new_capacity,col_sources,col_targets))

        return ret

    def slices_from_guid(self,guid):
        idx = self.guids.index(guid)
        starts = self.starts[idx]
        sizes = self.sizes[idx]
        return (slice(start,start+size,1) for start,size in zip(starts,sizes))

    #def as_class_id_table(self):
    #    ids = self.class_ids
    #    idx = 0
    #    cur_id = ids[idx]
    #    id = ids[idx]
    #    result = list()
    #    while idx < len(ids)
    #      tmp_result = TableRow(*(0,)*self.__row_length)
    #      while id == cur_id:
          
    #def __len__(self):  return len(self.guids)
    #def __iter__(self): return iter(self.guids)
    #def __contains__(self,key): return key in self.guids
    #def keys(self): return tuple(self.guids)
    #def values(self): return tuple(self.rows)
    #def items(self): return zip(self.guids,self.rows)

    ##def add_key(self,key,default=None):
    ##    assert key not in self.ids, "key %s already exists in table" % (key,)
    ##    self.ids.append(key)
    ##    if default is None:
    ##      self.rows.append(TableRow(*(0,)*self.__row_length))
    ##    else:
    ##      assert len(value) == self.__row_length,\
    ##          "%s does not have len %s"%(value,self.__row_length)
    ##      self.rows.append(TableRow(*value))

    #def get_guid(self,key):
    #    if key in self.guids:
    #        return self.rows[self.guids.index(key)]
    #    else:
    #        return TableRow(*(0,)*self.__row_length)
    #       
    #def __getitem__(self,key):
    #    assert key in self.guids, "guid %s not in Table" % (key,) 
    #    return self.rows[self.guids.index(key)]

    #def __setitem__(self,key,value):
    #    #TODO should this insert into proper class_id?
    #    assert key in self.guids, "Key %s not in table Table" % (key,) 
    #    assert len(value) == self.__row_length,\
    #        "%s does not have len %s"%(value,self.__row_length)
    #    self.rows[self.guids.index(key)] = TableRow(*value)

    #def __delitem__(self,key):
    #    raise AttributeError("Table does not support removal of keys")

    def show_sizes(self):
        formatter = self.__row_format.format
        ret_str = " guid"
        ret_str += formatter(*self.__col_names)
        ret_str += "\n"
        for guid,size_tuple in zip(self.guids, self.sizes):
          ret_str += "{:>5}".format(guid)
          ret_str += formatter(*size_tuple.values)
          ret_str += "\n"
        return ret_str

    def show_starts(self):
        formatter = self.__row_format.format
        ret_str = " guid"
        ret_str += formatter(*self.__col_names)
        ret_str += "\n"
        for guid,size_tuple in zip(self.guids, self.starts):
          ret_str += "{:>5}".format(guid)
          ret_str += formatter(*size_tuple.values)
          ret_str += "\n"
        return ret_str

    def __str__(self):
        return "<Table: "+' '.join(self.__col_names)+">"

    #def column_names_from_mask(self,mask):
    #    '''takes a mask as a tuple or integer (where the binary representation
    #    of the integer is the mask) and returns only those names.

    #    (0,0,1,1) and 3 are identical masks'''

    #    names = self.__col_names
    #    if isinstance(mask,int):
    #        mask = bin(mask)[2:]
    #        return tuple(name for name,exists in zip(names[::-1],mask[::-1]))
    #    elif isinstance(mask,tuple):
    #        raise NotImplementedError("easy to implement if needed")

if __name__ == '__main__':
    t = Table(('one','two'),((1,0),(1,1),(0,1)))
    try:
      t.stage_add(1,(3,3,3))
    except AssertionError:
      pass
    else:
      raise AssertionError("added three columns to two column table")

    #test adds and compression work
    t.stage_add(1,(0,3)) #added third
    t.stage_add(2,(3,0)) #this will be added first, because it is class_id == (1,0)
    t.stage_add(3,(3,3)) #added second

    if True: #for indentation
      #staging a guid already staged should over-write it
      try:
        t.stage_add(1,(10,10))
      except AssertionError:
        pass
      else:
        print("Test failed: re-added staged guid")

    for capacity, sources, targets in t.compress():
      assert capacity == 6, "capacity set to %s instead of 6" % alloc
      assert not sources, "no data should be moved:" + str(zip(sources,targets))


    #check that data ends up where it should
    expected = [(slice(0,3,1),slice(0,0,1)),
                (slice(3,6,1),slice(0,3,1)),
                (slice(6,6,1),slice(3,6,1)),]
    #print "starts:\n",t.print_starts()
    #print "sizes:\n",t.print_sizes()
    
    for guid,e in zip((2,3,1),expected):
        this_slice = tuple(t.slices_from_guid(guid))
        assert this_slice == e, "got wrong slices for guid: %s"%guid

    #test that adding an already allocated guid is illegal
    try:
      t.stage_add(1,(10,10))
    except AssertionError:
      pass
    else:
      print("Test failed:  re-added allocated guid")
      
    #test adding an entity to a non-empty table
    t.stage_add(4,(10,10))
    print("staged_adds:",t._staged_adds)

    for n, (capacity, sources, targets) in enumerate(t.compress()):
      assert capacity == 16, "capacity set to %s instead of 16" % alloc
      if n == 0:
        assert not sources and not targets, "first component does not move"
      elif n == 1:
        assert sources == (slice(3,6,1),), "guid 1 started at slice(3,6,1)"
        assert targets == (slice(13,16,1),), "guid 1 moves to slice(13,16,1)"

    #test getting slices for sections
    #TODO need to test that non-continuous columns fail and other edge cases
    t = Table(('one','two'),((1,0),(1,1),(0,1)))
    t.stage_add(1 ,(0,3)) 
    t.stage_add(2 ,(0,3)) 
    t.stage_add(3 ,(0,3)) 
    t.stage_add(4 ,(0,3)) 
    t.stage_add(5 ,(0,3)) 
    t.stage_add(6 ,(3,0)) 
    t.stage_add(7 ,(3,0)) 
    t.stage_add(8 ,(3,0)) 
    t.stage_add(9 ,(3,0)) 
    t.stage_add(10,(3,0)) 
    t.stage_add(13,(3,3)) 
    t.stage_add(14,(3,3)) 
    t.stage_add(15,(3,3)) 
    t.stage_add(16,(3,3)) 
    t.stage_add(17,(3,3)) 
    t.stage_add(18,(3,3)) 
    t.compress()
    expected = {(1,0):slice(0,5,1),(1,1):slice(5,11,1),(0,1):slice(11,None,1)}
    assert t.section_slices()==expected, "section_slices should return expected result"
    assert t.mask_slices(('one','two'),())[0] == {'one':slice(15, 33, None), 'two':slice(0, 18, None)}
