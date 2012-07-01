# import sys
# import copy

# from django.db.models.base import subclass_exception
# from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, FieldError
# from django.db.models.loading import register_models, get_model
# from django.db.models.fields.related import OneToOneField

# from semantic.rdf.models.options import Options


# class SemanticModelBase(type):
#     """
#     Metaclass for all models.
#     """
#     def __new__(cls, name, bases, attrs):
#         super_new = super(SemanticModelBase, cls).__new__
#         parents = [b for b in bases if isinstance(b, SemanticModelBase)]
#         if not parents:
#             # If this isn't a subclass of Model, don't do anything special.
#             return super_new(cls, name, bases, attrs)

#         # Create the class.
#         module = attrs.pop('__module__')
#         new_class = super_new(cls, name, bases, {'__module__': module})
#         attr_meta = attrs.pop('Meta', None)
#         abstract = getattr(attr_meta, 'abstract', False)
#         if not attr_meta:
#             meta = getattr(new_class, 'Meta', None)
#         else:
#             meta = attr_meta
#         base_meta = getattr(new_class, '_meta', None)

#         if getattr(meta, 'app_label', None) is None:
#             # Figure out the app_label by looking one level up.
#             # For 'django.contrib.sites.models', this would be 'sites'.
#             model_module = sys.modules[new_class.__module__]
#             kwargs = {"app_label": model_module.__name__.split('.')[-2]}
#         else:
#             kwargs = {}

#         new_class.add_to_class('_meta', Options(meta, **kwargs))
#         if not abstract:
#             new_class.add_to_class('DoesNotExist', subclass_exception('DoesNotExist',
#                     tuple(x.DoesNotExist
#                             for x in parents if hasattr(x, '_meta') and not x._meta.abstract)
#                                     or (ObjectDoesNotExist,), module))
#             new_class.add_to_class('MultipleObjectsReturned', subclass_exception('MultipleObjectsReturned',
#                     tuple(x.MultipleObjectsReturned
#                             for x in parents if hasattr(x, '_meta') and not x._meta.abstract)
#                                     or (MultipleObjectsReturned,), module))
#             if base_meta and not base_meta.abstract:
#                 # Non-abstract child classes inherit some attributes from their
#                 # non-abstract parent (unless an ABC comes before it in the
#                 # method resolution order).
#                 if not hasattr(meta, 'ordering'):
#                     new_class._meta.ordering = base_meta.ordering
#                 if not hasattr(meta, 'get_latest_by'):
#                     new_class._meta.get_latest_by = base_meta.get_latest_by

#         is_proxy = new_class._meta.proxy

#         if getattr(new_class, '_default_manager', None):
#             if not is_proxy:
#                 # Multi-table inheritance doesn't inherit default manager from
#                 # parents.
#                 new_class._default_manager = None
#                 new_class._base_manager = None
#             else:
#                 # Proxy classes do inherit parent's default manager, if none is
#                 # set explicitly.
#                 new_class._default_manager = new_class._default_manager._copy_to_model(new_class)
#                 new_class._base_manager = new_class._base_manager._copy_to_model(new_class)

#         # Bail out early if we have already created this class.
#         m = get_model(new_class._meta.app_label, name, False)
#         if m is not None:
#             return m

#         # Add all attributes to the class.
#         for obj_name, obj in attrs.items():
#             new_class.add_to_class(obj_name, obj)

#         # All the fields of any type declared on this model
#         new_fields = new_class._meta.local_fields + \
#                      new_class._meta.local_many_to_many + \
#                      new_class._meta.virtual_fields
#         field_names = set([f.name for f in new_fields])

#         # Basic setup for proxy models.
#         if is_proxy:
#             base = None
#             for parent in [cls for cls in parents if hasattr(cls, '_meta')]:
#                 if parent._meta.abstract:
#                     if parent._meta.fields:
#                         raise TypeError("Abstract base class containing model fields not permitted for proxy model '%s'." % name)
#                     else:
#                         continue
#                 if base is not None:
#                     raise TypeError("Proxy model '%s' has more than one non-abstract model base class." % name)
#                 else:
#                     base = parent
#             if base is None:
#                     raise TypeError("Proxy model '%s' has no non-abstract model base class." % name)
#             if (new_class._meta.local_fields or
#                     new_class._meta.local_many_to_many):
#                 raise FieldError("Proxy model '%s' contains model fields." % name)
#             while base._meta.proxy:
#                 base = base._meta.proxy_for_model
#             new_class._meta.setup_proxy(base)

#         # Do the appropriate setup for any model parents.
#         o2o_map = dict([(f.rel.to, f) for f in new_class._meta.local_fields
#                 if isinstance(f, OneToOneField)])

#         for base in parents:
#             original_base = base
#             if not hasattr(base, '_meta'):
#                 # Things without _meta aren't functional models, so they're
#                 # uninteresting parents.
#                 continue

#             parent_fields = base._meta.local_fields + base._meta.local_many_to_many
#             # Check for clashes between locally declared fields and those
#             # on the base classes (we cannot handle shadowed fields at the
#             # moment).
#             for field in parent_fields:
#                 if field.name in field_names:
#                     raise FieldError('Local field %r in class %r clashes '
#                                      'with field of similar name from '
#                                      'base class %r' %
#                                         (field.name, name, base.__name__))
#             if not base._meta.abstract:
#                 # Concrete classes...
#                 while base._meta.proxy:
#                     # Skip over a proxy class to the "real" base it proxies.
#                     base = base._meta.proxy_for_model
#                 if base in o2o_map:
#                     field = o2o_map[base]
#                 elif not is_proxy:
#                     attr_name = '%s_ptr' % base._meta.module_name
#                     field = OneToOneField(base, name=attr_name,
#                             auto_created=True, parent_link=True)
#                     new_class.add_to_class(attr_name, field)
#                 else:
#                     field = None
#                 new_class._meta.parents[base] = field
#             else:
#                 # .. and abstract ones.
#                 for field in parent_fields:
#                     new_class.add_to_class(field.name, copy.deepcopy(field))

#                 # Pass any non-abstract parent classes onto child.
#                 new_class._meta.parents.update(base._meta.parents)

#             # Inherit managers from the abstract base classes.
#             new_class.copy_managers(base._meta.abstract_managers)

#             # Proxy models inherit the non-abstract managers from their base,
#             # unless they have redefined any of them.
#             if is_proxy:
#                 new_class.copy_managers(original_base._meta.concrete_managers)

#             # Inherit virtual fields (like GenericForeignKey) from the parent
#             # class
#             for field in base._meta.virtual_fields:
#                 if base._meta.abstract and field.name in field_names:
#                     raise FieldError('Local field %r in class %r clashes '\
#                                      'with field of similar name from '\
#                                      'abstract base class %r' % \
#                                         (field.name, name, base.__name__))
#                 new_class.add_to_class(field.name, copy.deepcopy(field))

#         if abstract:
#             # Abstract base models can't be instantiated and don't appear in
#             # the list of models for an app. We do the final setup for them a
#             # little differently from normal models.
#             attr_meta.abstract = False
#             new_class.Meta = attr_meta
#             return new_class

#         new_class._prepare()
#         register_models(new_class._meta.app_label, new_class)

#         # Because of the way imports happen (recursively), we may or may not be
#         # the first time this model tries to register with the framework. There
#         # should only be one class for each model, so we always return the
#         # registered version.
#         return get_model(new_class._meta.app_label, name, False)

#     def copy_managers(cls, base_managers):
#         # This is in-place sorting of an Options attribute, but that's fine.
#         base_managers.sort()
#         for _, mgr_name, manager in base_managers:
#             val = getattr(cls, mgr_name, None)
#             if not val or val is manager:
#                 new_manager = manager._copy_to_model(cls)
#                 cls.add_to_class(mgr_name, new_manager)

#     def add_to_class(cls, name, value):
#         if hasattr(value, 'contribute_to_class'):
#             value.contribute_to_class(cls, name)
#         else:
#             setattr(cls, name, value)

#     def _prepare(cls):
#         """
#         Creates some methods once self._meta has been populated.
#         """
#         opts = cls._meta
#         opts._prepare(cls)

#         if opts.order_with_respect_to:
#             cls.get_next_in_order = curry(cls._get_next_or_previous_in_order, is_next=True)
#             cls.get_previous_in_order = curry(cls._get_next_or_previous_in_order, is_next=False)
#             # defer creating accessors on the foreign class until we are
#             # certain it has been created
#             def make_foreign_order_accessors(field, model, cls):
#                 setattr(
#                     field.rel.to,
#                     'get_%s_order' % cls.__name__.lower(),
#                     curry(method_get_order, cls)
#                 )
#                 setattr(
#                     field.rel.to,
#                     'set_%s_order' % cls.__name__.lower(),
#                     curry(method_set_order, cls)
#                 )
#             add_lazy_relation(
#                 cls,
#                 opts.order_with_respect_to,
#                 opts.order_with_respect_to.rel.to,
#                 make_foreign_order_accessors
#             )

#         # Give the class a docstring -- its definition.
#         if cls.__doc__ is None:
#             cls.__doc__ = "%s(%s)" % (cls.__name__, ", ".join([f.attname for f in opts.fields]))

#         if hasattr(cls, 'get_absolute_url'):
#             cls.get_absolute_url = update_wrapper(curry(get_absolute_url, opts, cls.get_absolute_url),
#                                                   cls.get_absolute_url)

#         signals.class_prepared.send(sender=cls)


from django.db.models.base import ModelBase, Model

from semantic.rdf.models.fields import AutoSemanticField
from semantic.rdf.models.manager import SemanticManager


class SemanticModelBase(ModelBase):
    pass


# class SemanticModelState(object):
#     """
#     A class for storing instance state
#     """
#     def __init__(self, db=None):
#         self.db = db


class SemanticModel(Model):
    # __metaclass__ = SemanticModelBase
    uri = AutoSemanticField()
    objects = SemanticManager()

    class Meta:
        abstract = True

    # def __init__(self, *args, **kwargs):
    #     # Set up the storage for instance state
    #     self._state = SemanticModelState()
