from builtins import (object, str)
from future.utils import with_metaclass

import abc

from copy import deepcopy


class Container(with_metaclass(abc.ABCMeta, object)):
    '''Abstract base class for storing object components.

    '''
    def __init__(self):
        '''**Initialisation**

A container is initialised with no parameters. Components are set
after initialisation with the `_set_component` method.

        '''
        self._components = {}
    #--- End: def
        
    def __repr__(self):
        '''x.__repr__() <==> repr(x)

        '''
        return '<{0}: {1}>'.format(self.__class__.__name__, str(self))
    #--- End: def

    def __str__(self):
        '''x.__str__() <==> str(x)

        '''
        out = sorted(self._components)
        return ', '.join(out)
    #--- End: def

    def _del_component(self, component):
        '''Remove a component.

.. seealso:: `_get_component`, `_has_component`, `_set_component`

:Parameters:

    component: 
        The name of the component to be removed.

:Returns:

     out:
        The removed component, or `None` if the component was not set.

:Examples:

>>> f._set_component('ncvar', 'air_temperature')
>>> f._has_component('ncvar')
True
>>> f._get_component('ncvar')
'air_temperature'
>>> f._del_component('ncvar')
'air_temperature'
>>> f._has_component('ncvar')
False

        '''
        return self._components.pop(component, None)
    #--- End: def

    def _get_component(self, component, *default):
        '''Return a component

.. seealso:: `_del_component`, `_has_component`, `_set_component`

:Parameters:

    component: 
        The name of the component to be returned.

    default: optional
        If the component has not been set then the *default* parameter
        is returned, if provided.

:Returns:

     out:
        The component. If the component has not been set then the
        *default* parameter is returned, if provided.

:Examples:

>>> f._set_component('ncvar', 'air_temperature')
>>> f._has_component('ncvar')
True
>>> f._get_component('ncvar')
'air_temperature'
>>> f._del_component('ncvar')
'air_temperature'
>>> f._has_component('ncvar')
False

        '''
        value = self._components.get(component)
        
        if value is None:
            if default:
                return default[0]

            raise AttributeError("{!r} object has no {!r} component".format(
                self.__class__.__name__, component))
            
        return value
    #--- End: def

    def _has_component(self, component):
        '''Whether a component has been set.

.. seealso:: `_del_component`, `_get_component`, `_set_component`

:Parameters:

    component: 
        The name of the component.

:Returns:

     out: `bool`
        True if the component has been set, otherwise False.

:Examples:

>>> f._set_component('ncvar', 'air_temperature')
>>> f._has_component('ncvar')
True
>>> f._get_component('ncvar')
'air_temperature'
>>> f._del_component('ncvar')
'air_temperature'
>>> f._has_component('ncvar')
False

        '''
        return component in self._components
    #--- End: def

    def _set_component(self, component, value, copy=True):
        '''Set a component.

.. seealso:: `_del_component`, `_get_component`, `_has_component`

:Parameters:

    component: `str`
        The name of the component.

    value:
        The value for the component.

:Returns:

     `None`

:Examples:


>>> f._set_component('ncvar', 'air_temperature')
>>> f._has_component('ncvar')
True
>>> f._get_component('ncvar')
'air_temperature'
>>> f._del_component('ncvar')
'air_temperature'
>>> f._has_component('ncvar')
False

        '''
        if copy:
            value = deepcopy(value)
            
        self._components[component] = value
    #--- End: def

    @abc.abstractmethod
    def copy(self):
        '''Return a deep copy.

``f.copy()`` is equivalent to ``copy.deepcopy(f)``.

:Examples 1:

>>> g = f.copy()

:Returns:

    out:
        The deep copy.

        '''
        raise NotImplementedError()
    #--- End: def
    
#--- End: class
