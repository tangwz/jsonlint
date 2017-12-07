# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import itertools

from jsonlint.compat import string_types
from jsonlint.i18n import DummyTranslations
from jsonlint.validators import StopValidation
from jsonlint.utils import unset_value


class Field(object):
    """
    Field base class
    """
    errors = tuple()
    process_errors = tuple()
    raw_data = None
    validators = tuple()
    _jsonfield = True
    _translations = DummyTranslations()

    def __new__(cls, *args, **kwargs):
        if '_json' in kwargs and '_name' in kwargs:
            return super(Field, cls).__new__(cls)
        else:
            return UnboundField(cls, *args, **kwargs)

    def __init__(self, validators=None, filters=tuple(), description='',
                 id=None, default=None, _json=None, _name=None, _prefix='',
                 _translations=None, _meta=None):
        """
        Construct a new field.

        :param validators:
            A sequence of validators to call when `validate` is called.
        :param filters:
            A sequence of filters which are run on input data by `process`.
        :param description:
            A description for the field, typically used for help text.
        :param id:
            An id to use for the field. A reasonable default is set by the class,
            and you shouldn't need to set this manually.
        :param default:
            The default value to assign to the field, if no data is provided.
            May be a callable.
        :param _json:
            The json holding this field. It is passed by the json itself during
            construction. You should never pass this value yourself.
        :param _name:
            The name of this field, passed by the enclosing json during its
            construction. You should never pass this value yourself.
        :param _prefix:
            The prefix to prepend to the json name of this field, passed by
            the enclosing form during construction.
        :param _translations:
            A translations object providing message translations. Usually
            passed by the enclosing json during construction. See
            :doc:`I18n docs <i18n>` for information on message translations.
        :param _meta:
            If provided, this is the 'meta' instance from the form. You usually
            don't pass this yourself.

        If `_json` and `_name` isn't provided, an :class:`UnboundField` will be
        returned instead. Call its :func:`bind` method with a json instance and
        a name to construct the field
        """
        if _translations is not None:
            self._translations = _translations

        if _meta is not None:
            self.meta = _meta
        elif _json is not None:
            self.meta = _json.meta
        else:
            raise TypeError("Must provide one of _json or _meta")

        self.default = default
        self.description = description
        self.filters = filters
        self.flags = Flags()
        self.name = _prefix + _name
        self.short_name = _name
        self.type = type(self).__name__
        self.validators = validators or list(self.validators)

        self.id = id or self.name

        for v in itertools.chain(self.validators):
            flags = getattr(v, 'field_flags', ())
            for f in flags:
                setattr(self.flags, f, True)

    def __unicode__(self):
        return self()

    def __str__(self):
        return self()

    def __call__(self):
        return self.data

    def gettext(self, string):
        """
        Get a translation for the given message.

        This proxies for the internal translations object.

        :param string: A unicode string to be translated.
        :return: A unicode string which is the translated output.
        """
        return self._translations.gettext(string)

    def ngettext(self, singular, plural, n):
        """
        Get a translation for a message which can be pluralized.

        :param singular: The singular json of the message.
        :param plural: The plural json of the message.
        :param n: The number of elements this message is referring to
        """
        return self._translations.ngettext(singular, plural, n)

    def validate(self, data, extra_validators=tuple()):
        """
        Validates the field and returns True or False. `self.errors` will
        contain any errors raised during validation. This is usually only
        called by `Json.validate`.

        Subfields shouldn't override this, but rather override either
        `pre_validate`, `post_validate` or both, depending on needs.

        :param data: The data the field belongs to.
        :param extra_validators: A sequence of extra validators to run.
        :return: True or False.
        """
        self.errors = list(self.process_errors)
        stop_validation = False

        # Call pre_validate
        try:
            self.pre_validate(data)
        except StopValidation as e:
            if e.args and e.args[0]:
                self.errors.append(e.args[0])
            stop_validation = True
        except ValueError as e:
            self.errors.append(e.args[0])

        # Run validators
        if not stop_validation:
            chain = itertools.chain(self.validators, extra_validators)
            stop_validation = self._run_validation_chain(data, chain)

        # Call post_validate
        try:
            self.post_validate(data, stop_validation)
        except ValueError as e:
            self.errors.append(e.args[0])

        return len(self.errors) == 0

    def _run_validation_chain(self, data, validators):
        """
        Run a validation chain, stop ping if any validator raises StopValidation.

        :param data: The data instance this field belongs to.
        :param validators: a sequence or iterable of validator callables.
        :return: True if validation was stopped, False otherwise.
        """
        for validator in validators:
            try:
                validator(data, self)
            except StopValidation as e:
                if e.args and e.args[0]:
                    self.errors.append(e.args[0])
                return True
            except ValueError as e:
                self.errors.append(e.args[0])

        return False

    def pre_validate(self, data):
        """
        Override if you need field-level validation. Runs before any other
        validators.

        :param data: The data the field belongs to.
        """
        pass

    def post_validate(self, data, validation_stopped):
        """
        Override if you need to run any field-level validation tasks after
        normal validation. This shouldn't be needed in most cases.

        :param data: The data the field belongs to.
        :param validation_stopped:
            `True` if any validator raised StopValidation.
        """
        pass

    def process(self, jsondata, data=unset_value):
        """
        Process incoming data, calling process_data, process_jsondata as needed,
        and run filters.

        If `data` is not provided, process_data will be called on the field's
        default.

        Field subclasses usually won't override this, instead overriding the
        process_jsondata and process_data methods. Only override this for
        special advanced processing, such as when a field encapsulates many
        inputs.
        """
        self.process_errors = []
        if data is unset_value:
            try:
                data = self.default()
            except TypeError:
                data = self.default

        self.process_data(data)

        if jsondata is not None:
            if self.name in jsondata:
                self.raw_data = jsondata.get(self.name)

                try:
                    self.process_jsondata(self.raw_data)
                except ValueError as e:
                    self.process_errors.append(e.args[0])
            else:
                self.raw_data = []
                if not self.data:
                    self.process_jsondata(self.raw_data)

        try:
            for filter in self.filters:
                self.data = filter(self.data)
        except ValueError as e:
            self.process_errors.append(e.args[0])

    def process_data(self, value):
        """
        Process the Python data applied to this field and store the result.

        This will be called during json construction by the json's `kwargs` or
        `obj` argument.

        :param value: The python object containing the value to process.
        """
        self.data = value

    def process_jsondata(self, value):
        """
        Process data received over the wire from a json.

        This will be called during json construction with data supplied
        through the `jsondata` argument.

        :param value: A list of strings to process.
        """
        if value:
            self.data = value[0]

    def populate_obj(self, obj, name):
        """
        Populates `obj.<name>` with the field's data.

        :note: This is a destructive operation. If `obj.<name>` already exists,
               it will be overridden. Use with caution.
        """
        setattr(obj, name, self.data)


class UnboundField(object):
    _jsonfield = True
    creation_counter = 0

    def __init__(self, field_class, *args, **kwargs):
        UnboundField.creation_counter += 1
        self.field_class = field_class
        self.args = args
        self.kwargs = kwargs
        self.creation_counter = UnboundField.creation_counter

    def bind(self, data, name, prefix='', translations=None, **kwargs):
        kw = dict(
            self.kwargs,
            _json=data,
            _prefix=prefix,
            _name=name,
            _translations=translations,
            **kwargs
        )
        return self.field_class(*self.args, **kw)

    def __repr__(self):
        return '<UnboundField(%s, %r, %r)>' % (self.field_class.__name__, self.args, self.kwargs)


class Flags(object):
    """
    Holds a set of boolean flags as attributes.

    Accessing a non-existing attribute returns False for its value.
    """

    def __getattr__(self, name):
        if name.startswith('_'):
            return super(Flags, self).__getattr__(name)
        return False

    def __contains__(self, name):
        return getattr(self, name)

    def __repr__(self):
        flags = (name for name in dir(self) if not name.startswith('_'))
        return '<jsonlints.fields.Flags: {%s}>' % ', '.join(flags)


class StringField(Field):
    """
    This field is the base string field.
    """

    def process_jsondata(self, value):
        if isinstance(value, string_types):
            self.data = value
        else:
            self.data = ''


class IntegerField(Field):
    """
    A text field, except all input is coerced to an integer.
    """

    def process_jsondata(self, value):
        try:
            self.data = int(value)
        except (ValueError, TypeError):
            self.data = None
            raise ValueError(self.gettext('Not a valid integer value'))


class FloatField(Field):
    """
    A text field, except all input is coerced to an float.
    """

    def process_jsondata(self, value):
        try:
            self.data = float(value)
        except (ValueError, TypeError):
            self.data = None
            raise ValueError(self.gettext('Not a valid float value'))


class BooleanField(Field):
    """
    A boolean field.

    :param false_values:
        If provided, a sequence of strings each of which is an exact match
        string of what is considered a "false" value. Defaults to the tuple
        ``('false', '')``
    """
    false_values = ('false', '')

    def __init__(self, validators=None, false_values=None, **kwargs):
        super(BooleanField, self).__init__(validators, **kwargs)
        if false_values is not None:
            self.false_values = false_values

    def process_data(self, value):
        self.data = bool(value)

    def process_jsondata(self, value):
        if not value or value in self.false_values:
            self.data = False
        else:
            self.data = True


class DateTimeField(Field):
    """
    A text field which stores a `datetime.datetime` matching a format.
    """
    def __init__(self, validators=None, format='%Y-%m-%d %H:%M:%S', **kwargs):
        super(DateTimeField, self).__init__(validators, **kwargs)
        self.format = format

    def __call__(self, *args, **kwargs):
        if self.raw_data:
            return self.raw_data
        else:
            return self.data and self.data.strftime(self.format) or ''

    def process_jsondata(self, value):
        if value:
            try:
                self.data = datetime.datetime.strptime(value, self.format)
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid datetime value'))


class DateField(DateTimeField):
    """
    Same as DateTimeField, except stores a `datetime.date`.
    """

    def __init__(self, validators=None, format='%Y-%m-%d', **kwargs):
        super(DateField, self).__init__(validators, format, **kwargs)

    def process_jsondata(self, value):
        if value:
            try:
                self.data = datetime.datetime.strptime(value, self.format).date()
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid date value'))


class TimeField(DateTimeField):
    """
    Same as DateTimeField, except stores a `time`.
    """

    def __init__(self, validators=None, format='%H:%M', **kwargs):
        super(TimeField, self).__init__(validators, format, **kwargs)

    def process_jsondata(self, value):
        if value:
            try:
                self.data = datetime.datetime.strptime(value, self.format).time()
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid time value'))


class ObjectField(Field):
    """
    Encapsulate a json object as a field in another json.

    :param json_class:
        A subclass of Json that will be encapsulated.
    """
    def __init__(self, json_class, validators=None, **kwargs):
        super(ObjectField, self).__init__(validators, **kwargs)
        self.json_class = json_class
        self._obj = None
        if self.filters:
            raise TypeError('ObjectField cannot take filters, as the encapsulated data is not mutable.')
        if validators:
            raise TypeError('ObjectField does not accept any validators. Instead, define them on the enclosed json.')

    def process(self, jsondata, data=unset_value):
        if data is unset_value:
            try:
                data = self.default()
            except TypeError:
                data = self.default
            self._obj = data

        if isinstance(jsondata, dict):
            jsondata = jsondata.get(self.name)

        if isinstance(data, dict):
            self.json = self.json_class(jsondata=jsondata, **data)
        else:
            self.json = self.json_class(jsondata=jsondata, obj=data)

    def validate(self, data, extra_validators=tuple()):
        if extra_validators:
            raise TypeError('ObjectField does not accept in-line validators, as it gets errors from the enclosed json.')
        return self.json.validate()

    def populate_obj(self, obj, name):
        candidate = getattr(obj, name, None)
        if candidate is None:
            if self._obj is None:
                raise TypeError(
                    'populate_obj: cannot find a value to populate json the provided obj or input data/defaults')
            candidate = self._obj
            setattr(obj, name, candidate)

        self.json.populate_obj(candidate)

    def __iter__(self):
        return iter(self.json)

    def __getitem__(self, item):
        return self.json[item]

    def __getattr__(self, item):
        return getattr(self.json, item)

    @property
    def data(self):
        return self.json.data

    @property
    def errors(self):
        return self.json.errors


class ListField(Field):
    """
    Encapsulate an ordered list of multiple instances of the same field type,
    keeping data as a list.

    >>> authors = ListField(StringField([validators.DataRequired()]))

    :param unbound_field:
        A partially-instantiated field definition, just like that would be
        defined on a form directly.
    :param min_entries:
        if provided, always have at least this many entries on the field,
        creating blank ones if the provided input does not specify a sufficient
        amount.
    :param max_entries:
        accept no more than this many entries as input, even if more exist in
        jsondata.
    """

    def __init__(self, unbound_field, validators=None, min_entries=0,
                 max_entries=None, default=list(), **kwargs):
        super(ListField, self).__init__(validators, default=default, **kwargs)
        if self.filters:
            raise TypeError('ListField does not accept any filters. Instead, define them on the enclosed field.')
        assert isinstance(unbound_field, UnboundField), 'Field must be unbound, not a field class'
        self.unbound_field = unbound_field
        self.min_entries = min_entries
        self.max_entries = max_entries
        self.last_index = -1
        self._prefix = kwargs.get('_prefix', '')

    def process(self, jsondata, data=unset_value):
        self.process_errors = []
        self.entries = []

        if data is unset_value or not data:
            try:
                data = self.default()
            except TypeError:
                data = self.default

        if jsondata and isinstance(jsondata, dict):
            jdata = jsondata.get(self.name)

            try:
                self.process_jsondata(jdata)
            except ValueError as e:
                self.process_errors.append(e.args[0])
        else:
            for obj_data in data:
                self._add_entry(jsondata, obj_data)

        while len(self.entries) < self.min_entries:
            self._add_entry(jsondata)

    def process_jsondata(self, value):
        if isinstance(value, list):
            for d in value:
                self._add_entry(data=d)
        else:
            raise ValueError(self.gettext('Not a valid list value'))

    def validate(self, data, extra_validators=tuple()):
        self.errors = list(self.process_errors)

        for subfield in self.entries:
            if not subfield.validate(data):
                self.errors.append(subfield.errors)

        chain = itertools.chain(self.validators, extra_validators)
        self._run_validation_chain(data, chain)

        return len(self.errors) == 0

    def populate_obj(self, obj, name):
        raise NotImplementedError()

    def _add_entry(self, jsondata=None, data=unset_value, index=None):
        assert not self.max_entries or len(self.entries) < self.max_entries, \
            'You cannot have more than max_entries entries in this ListField'
        if index is None:
            index = self.last_index + 1
        self.last_index = index
        name = self.short_name
        id = index
        field = self.unbound_field.bind(data=None, name=name, prefix=self._prefix, id=id, _meta=self.meta,
                                        translations=self._translations)
        field.process(jsondata, data)
        self.entries.append(field)
        return field

    def append_entry(self, data=unset_value):
        """
        Create a new entry with optional default data.

        Entries added in this way will *not* receive formdata however, and can
        only receive object data.
        """
        return self._add_entry(data=data)

    def pop_entry(self):
        """ Removes the last entry from the list and returns it. """
        entry = self.entries.pop()
        self.last_index -= 1
        return entry

    def __iter__(self):
        return iter(self.entries)

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, index):
        return self.entries[index]

    @property
    def data(self):
        return [f.data for f in self.entries]
