from collections import MutableMapping, Sequence
from types import GeneratorType

class TableRow(Sequence):
    '''A tuple that can be added to another tuple of the same size'''
    def __init__(self,*values):
        if isinstance(values[0],GeneratorType):
          self.values = tuple(values[0])
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

    def __repr__(self):
        return "TableRow: %s" %(self.values,)

    def __len__(self):
        return len(self.values)

    def __getitem__(self,index):
        return self.values[index]


class Table(MutableMapping):
    '''an ordered dict of tuples representing an alloction table.

    Adding keys to a Table is rare, and accidentally adding a key rather than
    updating a key would be harmful and cause potentially hard to track errors,
    so implicitly adding a key with `table[new_key]=value` is not supported.

    use add_key(key, value) to create a new key.
    '''
    def __init__(self,column_names):
        self.__col_names = tuple(column_names)
        self.__row_length = len(column_names)
        self.__row_format = ''.join((" | {:>%s}"%(len(name)) for name in column_names))
        self.ids = list()
        self.rows = list()

    @property
    def column_names(self):
        return self.__col_names

    @property
    def columns(self):
        return zip(*self.rows)

    def __len__(self):  return len(self.ids)
    def __iter__(self): return iter(self.ids)
    def __contains__(self,key): return key in self.ids
    def keys(self): return tuple(self.ids)
    def values(self): return tuple(self.rows)
    def items(self): return zip(self.ids,self.rows)

    def add_key(self,key,default=None):
        assert key not in self.ids, "key %s already exists in table" % (key,)
        self.ids.append(key)
        if default is None:
          self.rows.append(TableRow(*(0,)*self.__row_length))
        else:
          assert len(value) == self.__row_length,\
              "%s does not have len %s"%(value,self.__row_length)
          self.rows.append(TableRow(*value))

    def get(self,key):
        if key in self.ids:
            return self.rows[self.ids.index(key)]
        else:
            return TableRow(*(0,)*self.__row_length)
           
    def __getitem__(self,key):
        assert key in self.ids, "Key %s not in table Table" % (key,) 
        return self.rows[self.ids.index(key)]

    def __setitem__(self,key,value):
        assert key in self.ids, "Key %s not in table Table" % (key,) 
        assert len(value) == self.__row_length,\
            "%s does not have len %s"%(value,self.__row_length)
        self.rows[self.ids.index(key)] = TableRow(*value)

    def __delitem__(self,key):
        raise AttributeError("Table does not support removal of keys")

    def __str__(self):
        formatter = self.__row_format.format
        ret_str = "Table:\n   id"
        ret_str += formatter(*self.__col_names)
        ret_str += "\n"
        for id,row in self.items():
          ret_str += "{:>5}".format(id)
          ret_str += formatter(*row.values)
          ret_str += "\n"
        return ret_str

    def column_names_from_mask(self,mask):
        '''takes a mask as a tuple or integer (where the binary representation
        of the integer is the mask) and returns only those names.

        (0,0,1,1) and 3 are identical masks'''

        names = self.__col_names
        if isinstance(mask,int):
            mask = bin(mask)[2:]
            return tuple(name for name,exists in zip(names[::-1],mask[::-1]))
        elif isinstance(mask,tuple):
            raise NotImplementedError("easy to implement if needed")
