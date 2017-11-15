# -*- coding: utf-8 -*-
from jsonlint.i18n import DummyTranslations
from jsonlint.validators import ValidationError, StopValidation


class DummyField(object):
    _translations = DummyTranslations()

    def __init__(self, data, errors=(), raw_data=None):
        self.data = data
        self.errors = list(errors)
        self.raw_data = raw_data

    def gettext(self, string):
        return self._translations.gettext(string)

    def ngettext(self, singular, plural, n):
        return self._translations.ngettext(singular, plural, n)


def grab_error_message(callable, form, field):
    try:
        callable(form, field)
    except ValidationError as e:
        return e.args[0]


def grab_stop_message(callable, form, field):
    try:
        callable(form, field)
    except StopValidation as e:
        return e.args[0]
