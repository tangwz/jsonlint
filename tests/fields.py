# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date, datetime as dt
from unittest import TestCase
from jsonlint import validators, meta
from jsonlint.fields import *
from jsonlint.jsons import Json
from jsonlint.compat import text_type
from jsonlint.utils import unset_value


class AttrDict(object):
    def __init__(self, *args, **kw):
        self.__dict__.update(*args, **kw)


def make_json(_name='F', **fields):
    return type(str(_name), (Json,), fields)


class DefaultsTest(TestCase):
    def test(self):
        expected = 42

        def default_callable():
            return expected

        test_value = StringField(default=expected).bind(Json(), 'a')
        test_value.process(None)
        self.assertEqual(test_value.data, expected)

        test_callable = StringField(default=default_callable).bind(Json(), 'a')
        test_callable.process(None)
        self.assertEqual(test_callable.data, expected)


class FlagsTest(TestCase):
    def setUp(self):
        t = StringField(validators=[validators.DataRequired()]).bind(Json(), 'a')
        self.flags = t.flags

    def test_existing_values(self):
        self.assertEqual(self.flags.required, True)
        self.assertTrue('required' in self.flags)
        self.assertEqual(self.flags.optional, False)
        self.assertTrue('optional' not in self.flags)

    def test_assignment(self):
        self.assertTrue('optional' not in self.flags)
        self.flags.optional = True
        self.assertEqual(self.flags.optional, True)
        self.assertTrue('optional' in self.flags)

    def test_unset(self):
        self.flags.required = False
        self.assertEqual(self.flags.required, False)
        self.assertTrue('required' not in self.flags)

    def test_repr(self):
        self.assertEqual(repr(self.flags), '<jsonlints.fields.Flags: {required}>')

    def test_underscore_property(self):
        self.assertRaises(AttributeError, getattr, self.flags, '_foo')
        self.flags._foo = 42
        self.assertEqual(self.flags._foo, 42)


class UnsetValueTest(TestCase):
    def test(self):
        self.assertEqual(str(unset_value), '<unset value>')
        self.assertEqual(repr(unset_value), '<unset value>')
        self.assertEqual(bool(unset_value), False)
        assert not unset_value
        self.assertEqual(unset_value.__nonzero__(), False)
        self.assertEqual(unset_value.__bool__(), False)


class FiltersTest(TestCase):
    class F(Json):
        a = StringField(default='  hello', filters=[lambda x: x.strip()])
        b = StringField(default='42', filters=[int, lambda x: -x])

    def test_working(self):
        json = self.F()
        self.assertEqual(json.a.data, 'hello')
        self.assertEqual(json.b.data, -42)
        assert json.validate()

    def test_failure(self):
        json = self.F({'a': '  foo bar  ', 'b': 'hi'})
        self.assertEqual(json.a.data, 'foo bar')
        self.assertEqual(json.b.data, 'hi')
        self.assertEqual(len(json.b.process_errors), 1)
        assert not json.validate()


class FieldTest(TestCase):
    class F(Json):
        a = StringField(default='hello')

    def setUp(self):
        self.field = self.F().a

    def test_unbound_field(self):
        unbound = self.F.a
        assert unbound.creation_counter != 0
        assert unbound.field_class is StringField
        self.assertEqual(unbound.args, ())
        self.assertEqual(unbound.kwargs, {'default': 'hello'})
        assert repr(unbound).startswith('<UnboundField(StringField')

    def test_str_coerce(self):
        self.assertTrue(isinstance(str(self.field), str))
        self.assertEqual(str(self.field), str(self.field()))

    def test_unicode_coerce(self):
        self.assertEqual(text_type(self.field), self.field())

    def test_process_jsondata(self):
        Field.process_jsondata(self.field, [42])
        self.assertEqual(self.field.data, 42)

    def test_meta_attribute(self):
        json = self.F()
        assert json.a.meta is json.meta

        json_meta = meta.DefaultMeta()
        field = StringField(_name='Foo', _json=None, _meta=json_meta)
        assert field.meta is json_meta

        self.assertRaises(TypeError, StringField, _name='foo', _json=None)


class PrePostTestField(StringField):
    def pre_validate(self, data):
        if self.data == "stoponly":
            raise validators.StopValidation()
        elif self.data.startswith("stop"):
            raise validators.StopValidation("stop with message")
        elif self.data == "v":
            raise ValueError("value error")

    def post_validate(self, data, stopped):
        if self.data == "p":
            raise ValueError("Post")
        elif stopped and self.data == "stop-post":
            raise ValueError("Post-stopped")


class PrePostValidationTest(TestCase):
    class F(Json):
        a = PrePostTestField(validators=[validators.Length(max=1, message="too long")])

    def _init_field(self, value):
        json = self.F(a=value)
        json.validate()
        return json.a

    def test_pre_stop(self):
        a = self._init_field("long")
        self.assertEqual(a.errors, ["too long"])

        stoponly = self._init_field("stoponly")
        self.assertEqual(stoponly.errors, [])

        stopmessage = self._init_field("stopmessage")
        self.assertEqual(stopmessage.errors, ["stop with message"])

        value_error = self._init_field("v")
        self.assertEqual(value_error.errors, ["value error"])

    def test_post(self):
        a = self._init_field("p")
        self.assertEqual(a.errors, ["Post"])
        stopped = self._init_field("stop-post")
        self.assertEqual(stopped.errors, ["stop with message", "Post-stopped"])


class StringFieldTest(TestCase):
    class F(Json):
        a = StringField()

    def test(self):
        json = self.F()
        self.assertEqual(json.a.data, None)
        self.assertEqual(json.a(), None)
        json = self.F({'a': 'hello'})
        self.assertEqual(json.a.data, 'hello')
        self.assertEqual(json.a(), 'hello')
        json = self.F({'b': 'hello'})
        self.assertEqual(json.a.data, '')
        # test unicode
        json = self.F({'a': '你好'})
        self.assertEqual(json.a.data, '你好')
        self.assertEqual(json.a(), '你好')


class IntegerFieldTest(TestCase):
    class F(Json):
        a = IntegerField()
        b = IntegerField(default=48)

    def test(self):
        json = self.F({'a': 'v', 'b': '-15'})
        self.assertEqual(json.a.data, None)
        self.assertEqual(json.a.raw_data, 'v')
        self.assertEqual(json.a(), None)
        self.assertEqual(json.b.data, -15)
        self.assertEqual(json.b(), -15)
        self.assertTrue(not json.a.validate(json))
        self.assertTrue(json.b.validate(json))
        json = self.F({'a': [], 'b': ''})
        self.assertEqual(json.a.data, None)
        self.assertEqual(json.a.raw_data, [])
        self.assertEqual(json.b.data, None)
        self.assertEqual(json.b.raw_data, '')
        self.assertTrue(not json.validate())
        self.assertEqual(len(json.b.process_errors), 1)
        self.assertEqual(len(json.b.errors), 1)
        json = self.F(b=9)
        self.assertEqual(json.b.data, 9)


class FloatFieldTest(TestCase):
    class F(Json):
        a = FloatField()
        b = FloatField(default=48.0)

    def test(self):
        json = self.F({'a': 'v', 'b': '-15.0'})
        self.assertEqual(json.a.data, None)
        self.assertEqual(json.a.raw_data, 'v')
        self.assertEqual(json.a(), None)
        self.assertEqual(json.b.data, -15.0)
        self.assertEqual(json.b(), -15.0)
        self.assertTrue(not json.a.validate(json))
        self.assertTrue(json.b.validate(json))
        json = self.F({'a': [], 'b': ''})
        self.assertEqual(json.a.data, None)
        self.assertEqual(json.a.raw_data, [])
        self.assertEqual(json.b.data, None)
        self.assertEqual(json.b.raw_data, '')
        self.assertTrue(not json.validate())
        self.assertEqual(len(json.b.process_errors), 1)
        self.assertEqual(len(json.b.errors), 1)
        json = self.F(b=9.0)
        self.assertEqual(json.b.data, 9.0)


class BooleanFieldTest(TestCase):
    class BoringJson(Json):
        bool1 = BooleanField()
        bool2 = BooleanField(default=True, false_values=())

    obj = AttrDict(bool1=None, bool2=True)

    def test_defaults(self):
        # Test with no post data to make sure defaults work
        json = self.BoringJson()
        self.assertEqual(json.bool1.raw_data, None)
        self.assertEqual(json.bool1.data, False)
        self.assertEqual(json.bool2.data, True)

    def test_with_postdata(self):
        json = self.BoringJson({'bool1': 'a'})
        self.assertEqual(json.bool1.raw_data, 'a')
        self.assertEqual(json.bool1.data, True)
        json = self.BoringJson({'bool1': 'false', 'bool2': 'false'})
        self.assertEqual(json.bool1.data, False)
        self.assertEqual(json.bool2.data, True)

    def test_with_model_data(self):
        json = self.BoringJson(obj=self.obj)
        self.assertEqual(json.bool1.data, False)
        self.assertEqual(json.bool1.raw_data, None)
        self.assertEqual(json.bool2.data, True)

    def test_with_postdata_and_model(self):
        json = self.BoringJson({'bool1': 'y'}, obj=self.obj)
        self.assertEqual(json.bool1.data, True)
        self.assertEqual(json.bool2.data, True)


class DateFieldTest(TestCase):
    class F(Json):
        a = DateField()
        b = DateField(format='%m/%d %Y')

    def test_basic(self):
        d = date(2008, 5, 7)
        json = self.F({'a': '2008-05-07', 'b': '05/07 2008'})
        self.assertEqual(json.a.data, d)
        self.assertEqual(json.a(), '2008-05-07')
        self.assertEqual(json.b.data, d)
        self.assertEqual(json.b(), '05/07 2008')

    def test_failure(self):
        json = self.F({'a': '2008-bb-cc', 'b': 'hi'})
        assert not json.validate()
        self.assertEqual(len(json.a.process_errors), 1)
        self.assertEqual(len(json.a.errors), 1)
        self.assertEqual(len(json.b.errors), 1)
        self.assertEqual(json.a.process_errors[0], 'Not a valid date value')


class TimeFieldTest(TestCase):
    class F(Json):
        a = TimeField()
        b = TimeField(format='%H:%M')

    def test_basic(self):
        d = dt(2008, 5, 5, 4, 30, 0, 0).time()
        # Basic test with both inputs
        json = self.F({'a': '4:30', 'b': '04:30'})
        self.assertEqual(json.a.data, d)
        self.assertEqual(json.a(), '4:30')
        self.assertEqual(json.b.data, d)
        self.assertEqual(json.b(), '04:30')
        self.assertTrue(json.validate())

        # Test with a missing input
        json = self.F({'a': '04'})
        self.assertFalse(json.validate())
        self.assertEqual(json.a.errors[0], 'Not a valid time value')


class DateTimeFieldTest(TestCase):
    class F(Json):
        a = DateTimeField()
        b = DateTimeField(format='%Y-%m-%d %H:%M')

    def test_basic(self):
        d = dt(2008, 5, 5, 4, 30, 0, 0)
        # Basic test with both inputs
        json = self.F({'a': '2008-05-05 04:30:00', 'b': '2008-05-05 04:30'})
        self.assertEqual(json.a.data, d)
        self.assertEqual(json.a(), '2008-05-05 04:30:00')
        self.assertEqual(json.b.data, d)
        self.assertEqual(json.b(), '2008-05-05 04:30')
        self.assertTrue(json.validate())

        # Test with a missing input
        json = self.F({'a': '2008-05-05'})
        self.assertFalse(json.validate())
        self.assertEqual(json.a.errors[0], 'Not a valid datetime value')

        json = self.F(a=d, b=d)
        self.assertTrue(json.validate())
        self.assertEqual(json.a(), '2008-05-05 04:30:00')

    def test_microseconds(self):
        d = dt(2011, 5, 7, 3, 23, 14, 424200)
        F = make_json(a=DateTimeField(format='%Y-%m-%d %H:%M:%S.%f'))
        form = F({'a': '2011-05-07 03:23:14.4242'})
        self.assertEqual(d, form.a.data)


class ObjectFieldTest(TestCase):
    def setUp(self):
        F = make_json(
            a=StringField(validators=[validators.DataRequired()]),
            b=StringField(),
        )
        self.F1 = make_json('F1', a=ObjectField(F))
        self.F2 = make_json('F2', a=ObjectField(F))

        make_inner = lambda: AttrDict(a='ddd')
        self.F3 = make_json('F3', a=ObjectField(F, default=make_inner))

    def test_jsondata(self):
        json = self.F1({'a': {'a': 'moo'}})
        self.assertEqual(json.a.json.a.name, 'a')
        self.assertEqual(json.a.a.data, 'moo')
        self.assertEqual(json.a['a'].data, 'moo')
        self.assertEqual(json.a['b'].data, '')
        self.assertTrue(json.validate())

    def test_iteration(self):
        self.assertEqual([x.name for x in self.F1().a], ['a', 'b'])

    def test_with_obj(self):
        obj = AttrDict(a=AttrDict(a='mmm'))
        json = self.F1(obj=obj)
        self.assertEqual(json.a.json.a.data, 'mmm')
        self.assertEqual(json.a.json.b.data, None)
        obj_inner = AttrDict(a=None, b='rawr')
        obj2 = AttrDict(a=obj_inner)
        json.populate_obj(obj2)
        self.assertTrue(obj2.a is obj_inner)
        self.assertEqual(obj_inner.a, 'mmm')
        self.assertEqual(obj_inner.b, None)

        json = self.F3()
        obj = AttrDict(a=None)
        json.populate_obj(obj)
        self.assertEqual(obj.a.a, 'ddd')

    def test_no_validators_or_filters(self):
        class A(Json):
            a = ObjectField(self.F1, validators=[validators.DataRequired()])

        self.assertRaises(TypeError, A)

        class B(Json):
            a = ObjectField(self.F1, filters=[lambda x: x])

        self.assertRaises(TypeError, B)

        class C(Json):
            a = ObjectField(self.F1)

            def validate_a(json, field):
                pass

        json = C()
        self.assertRaises(TypeError, json.validate)

    def test_populate_missing_obj(self):
        obj = AttrDict(a=None)
        obj2 = AttrDict(a=AttrDict(a='mmm'))
        json = self.F1()
        self.assertRaises(TypeError, json.populate_obj, obj)
        json.populate_obj(obj2)


class ListFieldTest(TestCase):
    t = StringField(validators=[validators.DataRequired()])

    def test_json(self):
        F = make_json(a=ListField(self.t))
        data = ['foo', 'hi', 'rawr']
        a = F(a=data).a
        self.assertEqual(a.entries[1].data, 'hi')
        self.assertEqual(a.entries[1].name, 'a')
        self.assertEqual(a.data, data)
        self.assertEqual(len(a.entries), 3)

        pdata = {'a': ['bleh', 'yarg', '', 'mmm']}
        json = F(pdata)
        self.assertEqual(len(json.a.entries), 4)
        self.assertEqual(json.a.data, ['bleh', 'yarg', '', 'mmm'])
        self.assertFalse(json.validate())

        json = F(pdata, data)
        self.assertEqual(json.a.data, ['bleh', 'yarg', '', 'mmm'])
        self.assertFalse(json.validate())

        pdata = {'a': ['a', 'b']}
        json = F(pdata, a=data)
        self.assertEqual(len(json.a.entries), 2)
        self.assertEqual(json['a'].data, ['a', 'b'])
        self.assertEqual(list(iter(json.a)), list(json.a.entries))

        pdata = {'a': 'xx'}
        json = F(pdata)
        self.assertFalse(json.validate())

    def test_enclosed_subjson(self):
        make_inner = lambda: AttrDict(a=None)
        F = make_json(
            a=ListField(ObjectField(make_json('FChild', a=self.t), default=make_inner))
        )
        data = [{'a': 'hello'}]
        json = F(a=data)
        self.assertEqual(json.a.data, data)
        self.assertTrue(json.validate())
        json.a.append_entry()
        self.assertEqual(json.a.data, data + [{'a': None}])
        self.assertFalse(json.validate())

        pdata = {'a': [{'a': 'foo'}, {'a': 'bar'}]}
        json = F(pdata, a=data)
        self.assertEqual(json.a.data, [{'a': 'foo'}, {'a': 'bar'}])
        self.assertTrue(json.validate())

        # Test failure on populate
        obj2 = AttrDict(a=42)
        self.assertRaises(NotImplementedError, json.populate_obj, obj2)

    def test_entry_management(self):
        J = make_json(a=ListField(self.t))
        a = J(a=['hello', 'bye']).a
        self.assertEqual(a.pop_entry().name, 'a')
        self.assertEqual(a.data, ['hello'])
        a.append_entry('orange')
        self.assertEqual(a.data, ['hello', 'orange'])
        self.assertEqual(a[-1].name, 'a')
        self.assertEqual(a.pop_entry().data, 'orange')
        self.assertEqual(a.pop_entry().name, 'a')
        self.assertRaises(IndexError, a.pop_entry)

    def test_min_max_entries(self):
        J = make_json(a=ListField(self.t, min_entries=1, max_entries=3))
        a = J().a
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0].data, None)
        big_input = ['foo', 'flaf', 'bar', 'baz']
        self.assertRaises(AssertionError, J, a=big_input)

    def test_validators(self):
        def validator(json, field):
            if field.data and field.data[0] == 'fail':
                raise ValueError('fail')
            elif len(field.data) > 2:
                raise ValueError('too many')

        J = make_json(a=ListField(self.t, validators=[validator]))

        jdata = {'a': ['hello', 'bye', 'test3']}
        json = J(jdata)
        assert not json.validate()
        self.assertEqual(json.a.errors, ['too many'])

        jdata['a'] = ['fail']
        json = J(jdata)
        assert not json.validate()
        self.assertEqual(json.a.errors, ['fail'])

        json = J({'a': ['']})
        assert not json.validate()
        self.assertEqual(json.a.errors, [['This field is required.']])

    def test_no_filters(self):
        my_filter = lambda x: x
        self.assertRaises(TypeError, ListField, self.t, filters=[my_filter], _json=Json(), _name='foo')

    def test_process_prefilled(self):
        data = ['foo', 'hi', 'rawr']

        class A(object):
            def __init__(self, a):
                self.a = a

        obj = A(data)
        J = make_json(a=ListField(self.t))
        # fill json
        json = J(obj=obj)
        self.assertEqual(len(json.a.entries), 3)
        # pretend to submit form unchanged
        pdata = {'a': ['foo', 'hi', 'rawr']}
        json.process(jsondata=pdata)
        # check if data still the same
        self.assertEqual(len(json.a.entries), 3)
        self.assertEqual(json.a.data, data)
