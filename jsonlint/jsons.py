# -*- coding: utf-8 -*-
import itertools
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
from jsonlint.compat import with_metaclass, iteritems, itervalues
from jsonlint.meta import DefaultMeta

__all__ = (
    'BaseJson',
    'Json',
)


class BaseJson(object):

    def __init__(self, fields, prefix='', meta=DefaultMeta()):
        if prefix and prefix[-1] not in '-_;:/.':
            prefix += '-'

        self.meta = meta
        self._prefix = prefix
        self._errors = None
        self._fields = OrderedDict()

        if hasattr(fields, 'items'):
            fields = fields.items()

        translations = self.meta.get_translations(self)
        extra_fields = []
        for name, unbound_field in itertools.chain(fields, extra_fields):
            options = dict(name=name, prefix=prefix, translations=translations)
            field = meta.bind_field(self, unbound_field, options)
            self._fields[name] = field

    def __iter__(self):
        return iter(itervalues(self._fields))

    def __contains__(self, name):
        return (name in self._fields)

    def __getitem__(self, name):
        return self._fields[name]

    def __setitem__(self, name, value):
        self._fields[name] = value.bind(data=self, name=name, prefix=self._prefix)

    def __delitem__(self, name):
        del self._fields[name]

    def populate_obj(self, obj):
        for name, field in iteritems(self._fields):
            field.populate_obj(obj, name)

    def process(self, jsondata=None, obj=None, data=None, **kwargs):
        jsondata = self.meta.wrap_jsondata(self, jsondata)

        if data is not None:
            kwargs = dict(data, **kwargs)

        for name, field, in iteritems(self._fields):
            if obj is not None and hasattr(obj, name):
                field.process(jsondata, getattr(obj, name))
            elif name in kwargs:
                field.process(jsondata, kwargs[name])
            else:
                field.process(jsondata)

    def validate(self, extra_validators=None):
        self._errors = None
        success = True
        for name, field in iteritems(self._fields):
            if extra_validators is not None and name in extra_validators:
                extra = extra_validators[name]
            else:
                extra = tuple()
            if not field.validate(self, extra):
                success = False
        return success

    @property
    def data(self):
        return dict((name, f.data) for name, f in iteritems(self._fields))

    @property
    def errors(self):
        if self._errors is None:
            self._errors = dict((name, f.errors) for name, f in iteritems(self._fields) if f.errors)
        return self._errors


class JsonMeta(type):
    def __init__(cls, name, bases, attrs):
        type.__init__(cls, name, bases, attrs)
        cls._unbound_fields = None
        cls._json_meta = None

    def __call__(cls, *args, **kwargs):
        if cls._unbound_fields is None:
            fields = []
            for name in dir(cls):
                if not name.startswith('_'):
                    unbound_field = getattr(cls, name)
                    if hasattr(unbound_field, '_jsonfield'):
                        fields.append((name, unbound_field))
            fields.sort(key=lambda x: (x[1].creation_counter, x[0]))
            cls._unbound_fields = fields

        if cls._json_meta is None:
            bases = []
            for mro_class in cls.__mro__:
                if 'Meta' in mro_class.__dict__:
                    bases.append(mro_class.Meta)
            cls._json_meta = type('Meta', tuple(bases), {})
        return type.__call__(cls, *args, **kwargs)

    def __setattr__(cls, name, value):
        if name == 'Meta':
            cls._json_meta = None
        elif not name.startswith('_') and hasattr(value, '_jsonfield'):
            cls._unbound_fields = None
        type.__setattr__(cls, name, value)

    def __delattr__(cls, name):
        if not name.startswith('_'):
            cls._unbound_fields = None
        type.__delattr__(cls, name)


class Json(with_metaclass(JsonMeta, BaseJson)):

    Meta = DefaultMeta

    def __init__(self, jsondata=None, obj=None, prefix='', data=None, meta=None, **kwargs):
        meta_obj = self._json_meta()
        if meta is not None and isinstance(meta, dict):
            meta_obj.update_values(meta)
        super(Json, self).__init__(self._unbound_fields, meta=meta_obj, prefix=prefix)

        for name, field in iteritems(self._fields):
            # Set all the fields to attributes so that they obscure the class
            # attributes with the same names.
            setattr(self, name, field)
        self.process(jsondata, obj, data=data, **kwargs)

    def __setitem__(self, name, value):
        raise TypeError('Fields may not be added to Json instances, only classes.')

    def __delitem__(self, name):
        del self._fields[name]
        setattr(self, name, None)

    def __delattr__(self, name):
        if name in self._fields:
            self.__delitem__(name)
        else:
            # This is done for idempotency, if we have a name which is a field,
            # we want to mask it by setting the value to None.
            unbound_field = getattr(self.__class__, name, None)
            if unbound_field is not None and hasattr(unbound_field, '_jsonfield'):
                setattr(self, name, None)
            else:
                super(Json, self).__delattr__(name)

    def validate(self):
        extra = {}
        for name in self._fields:
            inline = getattr(self.__class__, 'validate_%s' % name, None)
            if inline is not None:
                extra[name] = [inline]

        return super(Json, self).validate(extra)
