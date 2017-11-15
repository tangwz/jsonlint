# -*- coding: utf-8 -*-
try:
    import ujson as json
except ImportError:
    import json
from jsonlint import i18n
from jsonlint.compat import string_types


class DefaultMeta(object):
    """
    This is the default Meta class which defines all the default values and
    therefore also the 'API' of the class Meta interface.
    """

    # -- Basic json primitives

    def bind_field(self, data, unbound_field, options):
        """
        bind_field allows potential customization of how fields are bound.

        The default implementation simply passes the options to
        :meth:`UnboundField.bind`.

        :param data: The raw json data.
        :param unbound_field: The unbound field.
        :param options:
            A dictionary of options which are typically passed to the field.

        :return: A bound field
        """
        return unbound_field.bind(data=data, **options)

    def wrap_jsondata(self, jsondata, data):
        if isinstance(data, string_types):
            data = json.loads(data)
        return data

    # -- i18n
    locales = False
    cache_translations = True
    translations_cache = {}

    def get_translations(self, data):
        """
        Override in subclasses to provide alternate translations factory.
        See the i18n documentation for more.

        :param data: The data.
        :return: An object that provides gettext() and ngettext() methods.
        """
        locales = self.locales
        if locales is False:
            return None

        if self.cache_translations:
            # Make locales be a hashable value
            locales = tuple(locales) if locales else None

            translations = self.translations_cache.get(locales)
            if translations is None:
                translations = self.translations_cache[locales] = i18n.get_translations(locales)

            return translations

        return i18n.get_translations(locales)

    # -- General
    def update_values(self, values):
        """
        Given a dictionary of values, update values on this `Meta` instance.
        """
        for key, value in values.items():
            setattr(self, key, value)
