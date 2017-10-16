from os       import close
from sys      import getrefcount
from tempfile import mkstemp
from operator import mul

from numpy import empty   as numpy_empty
from numpy import full    as numpy_full
from numpy import load    as numpy_load
from numpy import ndarray as numpy_ndarray
from numpy import save    as numpy_save

from numpy.ma import array      as numpy_ma_array
from numpy.ma import is_masked  as numpy_ma_is_masked
from numpy.ma import masked_all as numpy_ma_masked_all

from ..functions import parse_indices, get_subspace, abspath
from ..constants import CONSTANTS

_debug = False

# ====================================================================
#
# FileArray object
# 
# ====================================================================

class FileArray(object):
    '''An array stored in a file.
    
.. note:: Subclasses must define the following methods:
          `!__getitem__`, `!__str__`, `!close` and `!open`.

    '''
    def __init__(self, **kwargs):
        '''
        
**Initialization**

:Parameters:

    file: `str`
        The netCDF file name in normalized, absolute form.

    dtype: `numpy.dtype`
        The numpy data type of the data array.

    ndim: `int`
        Number of dimensions in the data array.

    shape: `tuple`
        The data array's dimension sizes.

    size: `int`
        Number of elements in the data array.

'''
        self.__dict__ = kwargs

        f = getattr(self, 'file', None)
        if f is not None:
            self.file = abspath(f)
    #--- End: def
            
    def __deepcopy__(self, memo):
        '''

Used if copy.deepcopy is called on the variable.

'''
        return self.copy()
    #--- End: def

    def __repr__(self):
        '''

x.__repr__() <==> repr(x)

'''      
        return "<CFDM: {0}>".format(self.__class__.__name__, str(self))
    #--- End: def
     
    def __str__(self):
        '''

x.__str__() <==> str(x)

'''
        return "{0} in {1}".format(self.shape, self.file)
    #--- End: def
    
    def copy(self):
        '''Return a deep copy.

``f.copy() is equivalent to ``copy.deepcopy(f)``.

:Returns:

    out :
        A deep copy.

:Examples:

>>> g = f.copy()

        '''
        C = self.__class__
        new = C.__new__(C)
        new.__dict__ = self.__dict__.copy()
        return new
    #--- End: def
    
    def close(self):
        pass
    #--- End: def

    def open(self):
        pass
    #--- End: def

#--- End: class

# ====================================================================
#
# NumpyArray object
# 
# ====================================================================

class NumpyArray(Array):
    '''An numpy  array.

    '''
    def __init__(self, array, fill_value=None):
        '''
        
**Initialization**

:Parameters:

    file: `str`
        The netCDF file name in normalized, absolute form.

    dtype: `numpy.dtype`
        The numpy data type of the data array.

    ndim: `int`
        Number of dimensions in the data array.

    shape: `tuple`
        The data array's dimension sizes.

    size: `int`
        Number of elements in the data array.

        '''   
        self._array = array
    #--- End: def
            
    def __repr__(self):
        '''

x.__repr__() <==> repr(x)

'''      
        return repr(self._array)
    #--- End: def
     
    def __str__(self):
        '''

x.__str__() <==> str(x)

'''
        return str(self._array)
    #--- End: def

    def __getitem__(self, indices):
        '''

x.__getitem__(indices) <==> x[indices]

Returns a numpy array.

'''
        array = self._array

        indices = parse_indices(array.shape, indices)

        array = get_subspace(array, indices)

        if numpy.ma.isMA(array):
            array.set_fill_value(self.fill_Value)
    #--- End: def

    @property
    def ndim(self):
        return self._array.ndim

    @property
    def shape(self):
        return self._array.shape

    @property
    def size(self):
        return self._array.size

    @property
    def dtype(self):
        return self._array.dtype

#--- End: class

# ====================================================================
#
# NetCDFFileArray object
#
# ====================================================================

class NetCDFFileArray(FileArray):
    '''A sub-array stored in a netCDF file.
    
**Initialization**

:Parameters:

    file: `str`
        The netCDF file name in normalized, absolute form.

    dtype: `numpy.dtype`
        The numpy data type of the data array.

    ndim: `int`
        Number of dimensions in the data array.

    shape: `tuple`
        The data array's dimension sizes.

    size: `int`
        Number of elements in the data array.

    ncvar: `str`, optional
        The netCDF variable name containing the data array. Must be
        set if *varid* is not set.

    varid: `int`, optional
        The netCDF ID of the variable containing the data array. Must
        be set if *ncvar* is not set. Ignored if *ncvar* is set.

#    ragged: `int`, optional
#        Reduction in logical rank due to ragged array representation.
#
#    gathered: `int`, optional
#        Reduction in logical rank due to compression by gathering.

:Examples:

>>> import netCDF4
>>> import os
>>> nc = netCDF4.Dataset('file.nc', 'r')
>>> v = nc.variable['tas']
>>> a = NetCDFFileArray(file=os.path.abspath('file.nc'), ncvar='tas',
                        dtype=v.dtype, ndim=v.ndim, shape=v.shape,
                        size=v.size)

    '''
    def __getitem__(self, indices):
        '''

x.__getitem__(indices) <==> x[indices]

Returns a numpy array.

''' 
        nc = self.open()
        
        ncvar = getattr(self, 'ncvar', None)

        if ncvar is not None:
            # Get the variable by name
            array = nc.variables[ncvar][indices]
        else:
            # Get the variable by netCDF ID
            varid = self.varid
            for value in nc.variables.itervalues():
                if value._varid == varid:
                    array = value[indices]
                    break
        #--- End: if

        if not self.ndim:
            # Hmm netCDF4 has a thing for making scalar size 1 , 1d
            array = array.squeeze()

        # ------------------------------------------------------------
        # If approriate, collapse (by concatenation) the outermost
        # (fastest varying) dimension of string valued array into
        # memory. E.g. [['a','b','c']] becomes ['abc']
        # ------------------------------------------------------------
        if array.dtype.kind == 'S' and array.ndim > (self.ndim -
                                                     getattr(self, 'gathered', 0) -
                                                     getattr(self, 'ragged', 0)):
            strlen = array.shape[-1]
            
            new_shape = array.shape[0:-1]
            new_size  = long(reduce(mul, new_shape, 1))
            
            array = numpy_ma_resize(array, (new_size, strlen))
            
            array = array.filled(fill_value='')

            array = numpy_array([''.join(x).rstrip() for x in array],
                                dtype='S%d' % strlen)
            
            array = array.reshape(new_shape)

            array = numpy_ma_where(array=='', numpy_ma_masked, array)
        #--- End: if

        return array
    #--- End: def

    def __str__(self):
        '''

x.__str__() <==> str(x)

'''      
        name = getattr(self, 'ncvar', None)
        if name is None:
            name = self.varid

        return "%s%s in %s" % (name, self.shape, self.file)
    #--- End: def
    
    def close(self):
        '''

Close the file containing the data array.

If the file is not open then no action is taken.

:Returns:

    None

:Examples:

>>> f.close()

'''
        _close_netcdf_file(self.file)
    #--- End: def

    @property
    def  file_pointer(self):
        '''
'''
        offset = getattr(self, 'ncvar', None)
        if offset is None:
            offset = self.varid

        return (self.file, offset)
    #--- End: def

    def open(self):
        '''

Return a `netCDF4.Dataset` object for the file containing the data
array.

:Returns:

    out : netCDF4.Dataset

:Examples:

>>> f.open()
<netCDF4.Dataset at 0x115a4d0>

'''
        return _open_netcdf_file(self.file, 'r')
    #--- End: def

#--- End: class

# ====================================================================
#
# CompressedArray object
#
# ====================================================================

class CompressedArray(object):
    '''
'''
    def __init__(self, array, shape, compression):
        '''
        
**Initialization**

:Parameters:

    array: 

    shape: `tuple`
        The shape of the uncompressed array

    compression: `dict`
'''
        # DO NOT CHANGE IN PLACE
        self.array = array

        # DO NOT CHANGE IN PLACE
        self.compression = compression

        # DO NOT CHANGE IN PLACE
        self.shape = tuple(shape)

        # DO NOT CHANGE IN PLACE            
        self.ndim  = len(shape)

        # DO NOT CHANGE IN PLACE
        self.size  = long(reduce(mul, shape, 1))
    #---End: def

    def __getitem__(self, indices):
        '''

x.__getitem__(indices) <==> x[indices]

Returns a numpy array.

'''
        compression = self.compression
        (compression_type, uncompression) = self.compression.items()[0]
        
        # The compressed array
        array = self.array
        
        # Initialize the full, uncompressed output array with missing
        # data everywhere
        uarray = numpy_ma_masked_all(self.shape, dtype=array.dtype)

        r_indices = [slice(None)] * array.ndim
        p_indices = [slice(None)] * uarray.ndim        
        
        if compression_type == 'gathered':
            sample_axis           = uncompression['axis']
            uncompression_indices = uncompression['indices']
            
            compressed_axes = range(sample_axis, self.ndim - (array.ndim - sample_axis - 1))
            n_compressed_axes = len(compressed_axes)
            
            zzz = [reduce(mul, [shape[i] for i in compressed_axes[i:]], 1)
                   for i in range(1, n_compressed_axes)]
            
            zeros = [0] * n_compressed_axes
            for ii, b in enumerate(uncompression_indices):
                r_indices[sample_axis] = ii
                
                xxx = zeros[:]
                for i, z in enumerate(zzz):                
                    if b >= z:
                        (a, b) = divmod(b, z)
                        xxx[i] = a
                    xxx[-1] = b
                #--- End: for
                        
                for j, x in izip(compressed_axes, xxx):
                    p_indices[j] = x
                    
                uarray[p_indices] = r_data[r_indices]
            #--- End: for

        elif compression_type == 'DSG_contiguous':
            instance_axis  = uncompression['instance_axis']
            instance_index = uncompression['instance_index']
            element_axis   = uncompression['c_element_axis']
            sample_indices = uncompression['c_element_indices']
            p_indices[instance_axis] = instance_index
            p_indices[element_axis]  = slice(0, sample_indices.stop - sample_indices.start)
            
            uarray[tuple(p_indices)] = array[sample_indices]
            
            if _debug:
                print 'instance_axis    =', instance_axis
                print 'instance_index   =', instance_index
                print 'element_axis     =', element_axis
                print 'sample_indices   =', sample_indices
                print 'p_indices        =', p_indices
                print 'uarray.shape     =', uarray.shape
                print 'self.array.shape =', array.shape

        elif compression_type == 'DSG_indexed':
            instance_axis  = uncompression['instance_axis']
            instance_index = uncompression['instance_index']
            element_axis   = uncompression['i_element_axis']
            sample_indices = uncompression['i_element_indices']
            
            p_indices[instance_axis] = instance_index
            p_indices[element_axis]  = slice(0, len(sample_indices))
            
            uarray[tuple(p_indices)] = array[sample_indices]
            
            if _debug:
                print 'instance_axis    =', instance_axis
                print 'instance_index   =', instance_index
                print 'element_axis     =', element_axis
                print 'sample_indices   =', sample_indices
                print 'p_indices        =', p_indices
                print 'uarray.shape     =', uarray.shape
                print 'self.array.shape =', array.shape

        elif compression_type == 'DSG_indexed_contiguous':
            instance_axis     = uncompression['instance_axis']
            instance_index    = uncompression['instance_index']
            i_element_axis    = uncompression['i_element_axis']
            i_element_index   = uncompression['i_element_index']
            c_element_axis    = uncompression['c_element_axis']
            c_element_indices = uncompression['c_element_indices']
            
            p_indices[instance_axis]  = instance_index
            p_indices[i_element_axis] = i_element_index
            p_indices[c_element_axis] = slice(0, c_element_indices.stop - c_element_indices.start)
            
            uarray[tuple(p_indices)] = array[c_element_indices]
        else:
            raise ValueError("Unkown compression type: {}".format(compression_type))
        
        if indices is Ellipsis:
            return uarray
        else:
            if _debug:
                print 'indices =', indices
            indices = parse_indices(self.shape, indices)
            if _debug:
                print 'parse_indices(self.shape, indices) =', indices
                
            return get_subspace(uarray, indices)
    #--- End: def

    def __repr__(self):
        '''

x.__repr__() <==> repr(x)
        '''
        return "<CF %s: %s>" % (self.__class__.__name__, str(self.array))
    #--- End: def

    @property
    def dtype(self):
        return self.array.dtype

    @property    
    def file(self):
        '''The file on disk which contains the compressed array, or `None` of
the array is in memory.

:Examples:

>>> self.file
'/home/foo/bar.nc'

        '''        
        return getattr(self.array, 'file', None)
    #--- End: def

    def close(self):
        '''

Close all referenced open files.

:Returns:

    None

:Examples:

>>> f.close()

'''     
        if self.on_disk():
            self.array.close()
    #--- End: def

    def copy(self):
        '''
'''
        C = self.__class__
        new = C.__new__(C)
        new.__dict__ = self.__dict__.copy()
        return new
    #--- End: def

    def inspect(self):
        '''

Inspect the object for debugging.

.. seealso:: `cf.inspect`

:Returns: 

    None

'''
        print cf_inspect(self)
    #--- End: def
        
    def on_disk(self):
        '''True if and only if the compressed array is on disk as opposed to
in memory.

:Examples:

>>> a.on_disk()
True

        '''
        return not hasattr(self.array, '__array_interface__')
    #--- End: if

    def unique(self):
        '''
'''
        return getrefcount(self.array) <= 2
    #--- End: def
#--- End: class

