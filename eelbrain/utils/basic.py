"""
A few basic operations needed throughout Eelbrain

Created by Christian Brodbeck on 7/3/09.
"""

from collections import defaultdict
import os
import cPickle as pickle

import numpy as np

from eelbrain import ui


def common_prefix(names):
    """Find the longest common prefix of a list of strings

    Parameters
    ----------
    names : list of str
        List with strings.

    Returns
    -------
    prefix : str
        Longest common prefix.

    Notes
    -----
    Should work with other sequence types than :class:`str` as long as they
    support indexing and comparison (as in ``a[:i] == b[:i]``).
    """
    if len(names) == 0:
        return None
    elif len(names) == 1:
        return names[0]

    N = min(len(n) for n in names)
    ref = names[0]
    comp = names[1:]

    for i in xrange(1, N + 1):
        if not all(c[:i] == ref[:i] for c in comp):
            return ref[:i - 1]



class intervals:
    """Iterate over each successive pair in a sequence.

    Examples
    --------
    >>> for i in intervals([1, 2, 3, 45]):
    ...     print i
    ...
    (1, 2)
    (2, 3)
    (3, 45)
    """
    def __init__(self, seq):
        self.seq = seq
        self.i = 0
        if len(self.seq) < 2:
            raise StopIteration
    def __iter__(self):
        return self
    def next(self):
        self.i += 1
        if len(self.seq) <= self.i:
            raise StopIteration
        return self.seq[self.i - 1], self.seq[self.i]



class LazyProperty(object):
    "http://blog.pythonisito.com/2008/08/lazy-descriptors.html"
    def __init__(self, func):
        self._func = func
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__

    def __get__(self, obj, klass=None):
        if obj is None: return None
        result = obj.__dict__[self.__name__] = self._func(obj)
        return result



class keydefaultdict(defaultdict):
    "http://stackoverflow.com/a/2912455/166700"
    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        else:
            ret = self[key] = self.default_factory(key)
            return ret



def toTuple(items):
    """
    makes sure items is a tuple
    """
    if not type(items) in [list, tuple, set]:
        items = (items,)
    else:
        items = tuple(items)
    return items

def toList(items):
    """
    makes sure items is a list
    """
    if not type(items) in [list, tuple, set]:
        items = [items]
    else:
        items = list(items)
    return items



# IO operations

def add_ext(path, ext, multiple=False, ask_overwrite=True):
    """
    Adds ext to path;

    kwargs
    -----
    multiple=False:
        =False: if path has an extension, nothing will be done
        ='r', 'replace': existing extension will be replaced.
        ='a', 'add': extension will be added independent of existing extension
    """
    name, old_ext = os.path.splitext(path)
    # remove leading dots
    old_ext = old_ext.lstrip(os.path.extsep)
    ext = ext.lstrip(os.path.extsep)
    # modify
    if old_ext:
        if multiple in ['r', 'replace']:
            pass
        elif  (multiple in ['a', 'add'])  and  (old_ext != ext):
            ext = os.path.extsep.join([old_ext, ext])
        else:
            ext = old_ext

    path = os.path.extsep.join([name, ext])
    if ask_overwrite:
        if os.path.exists(path):
            if not ui.ask(title="Overwrite File?",
                          message="The File '%s' already exists. Overwrite the existing file?" % path):
                return None
    return path


def loadtable(path, d='\t', txt='"', dtype=float, txtcols=[], txtrows=[],
              empty=np.NaN):
    """
    loads a table from a file. If extension is '.pickled' or '.pickle', the
    file will simply be unpickled. Otherwise it will be read as a table-
    separated-values (TSV) file.

    kwargs
    ------
    d: delimiter
    txt: string indicator
    dtype: data type for conversion if not string
    textcols/textrows: columns and rows that should be interpreted as text
                       instead of dtype
    empty: replace empty strings with this value

    """
    name, ext = os.path.splitext(path)
    if ext in ['.pickled', '.pickle']:
        with open(path) as f:
            table = pickle.load(f)
    else:
        raw_table = []
        for line in open(path):
            row = line.replace('\n', '')
            if len(row) > 0:
                raw_table.append(row.split(d))
        # data conversion
        table = []
        for i, row in enumerate(raw_table):
            if i in txtrows:
                table.append(row)
            else:
                row_c = []
                for j, val in enumerate(row):
                    if j in txtcols:
                        row_c.append(val.replace(txt, ''))
                    else:
                        if len(val) == 0:
                            val_c = empty
                        elif val[0] == txt:
                            val_c = val.replace(txt, '')
                        else:
                            try:
                                val_c = dtype(val)
                            except:
                                val_c = val
                        row_c.append(val_c)
                table.append(row_c)
    return table


def test_attr_name(name, printname=None):
    """
    Test whether name is a proper attribute name. Raises an Error if it is not.

    :arg printname: use this argument if the name that should be printed in
        the error message diffes from the name to be tested (e.g. when name is
        formatted with dummy items)

    """
    assert isinstance(name, str)
    if printname is None:
        printname = name
    if name.startswith('_'):
        raise ValueError("Invalid ExpermentItem name: %r (Cannot start with"
                         "'_')" % printname)
    elif name[0].isdigit():
        raise ValueError("Invalid ExpermentItem name: %r (Cannot start with"
                         " a number)" % name)
    elif not name.replace('_', 'x').isalnum():
        raise ValueError("Invalid ExpermentItem name: %r (Must be alpha-"
                         "numeric & '_')" % printname)