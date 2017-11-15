from __future__ import unicode_literals

import json as pyjson
from unittest import TestCase

from jsonlint.jsons import BaseJson, Json
from jsonlint.meta import DefaultMeta
from jsonlint.fields import StringField, IntegerField
from jsonlint.validators import ValidationError


class BaseJsonTest(TestCase):
    def get_json(self, **kwargs):
        def validate_test(json, field):
            if field.data != 'foobar':
                raise ValidationError('error')

        return BaseJson({'test': StringField(validators=[validate_test])}, **kwargs)

    def test_data_proxy(self):
        json = self.get_json()
        json.process(test='foo')
        self.assertEqual(json.data, {'test': 'foo'})
        json.process(pyjson.dumps({'test': 'foo'}))
        self.assertEqual(json.data, {'test': 'foo'})

    def test_errors_proxy(self):
        json = self.get_json()
        json.process(test='foobar')
        json.validate()
        self.assertEqual(json.errors, {})

        json = self.get_json()
        json.process()
        json.validate()
        self.assertEqual(json.errors, {'test': ['error']})

    def test_contains(self):
        json = self.get_json()
        self.assertTrue('test' in json)
        self.assertTrue('abcd' not in json)

    def test_field_removal(self):
        json = self.get_json()
        del json['test']
        self.assertRaises(AttributeError, getattr, json, 'test')
        self.assertTrue('test' not in json)

    def test_field_adding(self):
        json = self.get_json()
        self.assertEqual(len(list(json)), 1)
        json['foo'] = StringField()
        self.assertEqual(len(list(json)), 2)
        json.process({'foo': 'hello'})
        self.assertEqual(json['foo'].data, 'hello')
        json['test'] = IntegerField()
        self.assertTrue(isinstance(json['test'], IntegerField))
        self.assertEqual(len(list(json)), 2)
        self.assertRaises(AttributeError, getattr, json['test'], 'data')
        json.process({'test': '1'})
        self.assertEqual(json['test'].data, 1)
        self.assertEqual(json['foo'].data, '')

    def test_populate_obj(self):
        m = type(str('Model'), (object, ), {})
        form = self.get_json()
        form.process(test='foobar')
        form.populate_obj(m)
        self.assertEqual(m.test, 'foobar')
        self.assertEqual([k for k in dir(m) if not k.startswith('_')], ['test'])

    def test_prefixes(self):
        json = self.get_json(prefix='foo')
        self.assertEqual(json['test'].name, 'foo-test')
        self.assertEqual(json['test'].short_name, 'test')
        self.assertEqual(json['test'].id, 'foo-test')
        json = self.get_json(prefix='foo.')
        json.process({'foo.test': 'hello', 'test': 'bye'})
        self.assertEqual(json['test'].data, 'hello')
        self.assertEqual(self.get_json(prefix='foo[')['test'].name, 'foo[-test')


class JsonMetaTest(TestCase):
    def test_monkeypatch(self):
        class J(Json):
            a = StringField()

        self.assertEqual(J._unbound_fields, None)
        J()
        self.assertEqual(J._unbound_fields, [('a', J.a)])
        J.b = StringField()
        self.assertEqual(J._unbound_fields, None)
        J()
        self.assertEqual(J._unbound_fields, [('a', J.a), ('b', J.b)])
        del J.a
        self.assertRaises(AttributeError, lambda: J.a)
        J()
        self.assertEqual(J._unbound_fields, [('b', J.b)])
        J._m = StringField()
        self.assertEqual(J._unbound_fields, [('b', J.b)])

    def test_subclassing(self):
        class A(Json):
            a = StringField()
            c = StringField()

        class B(A):
            b = StringField()
            c = StringField()
        A()
        B()

        self.assertTrue(A.a is B.a)
        self.assertTrue(A.c is not B.c)
        self.assertEqual(A._unbound_fields, [('a', A.a), ('c', A.c)])
        self.assertEqual(B._unbound_fields, [('a', B.a), ('b', B.b), ('c', B.c)])

    def test_class_meta_reassign(self):
        class MetaA:
            pass

        class MetaB:
            pass

        class J(Json):
            Meta = MetaA

        self.assertEqual(J._json_meta, None)
        assert isinstance(J().meta, MetaA)
        assert issubclass(J._json_meta, MetaA)
        J.Meta = MetaB
        self.assertEqual(J._json_meta, None)
        assert isinstance(J().meta, MetaB)
        assert issubclass(J._json_meta, MetaB)


class JsonTest(TestCase):
    class F(Json):
        test = StringField()

        def validate_test(json, field):
            if field.data != 'foobar':
                raise ValidationError('error')

    def test_validate(self):
        json = self.F(test='foobar')
        self.assertEqual(json.validate(), True)

        json = self.F()
        self.assertEqual(json.validate(), False)

    def test_field_adding_disabled(self):
        json = self.F()
        self.assertRaises(TypeError, json.__setitem__, 'foo', StringField())

    def test_field_removal(self):
        json = self.F()
        del json.test
        self.assertTrue('test' not in json)
        self.assertEqual(json.test, None)
        self.assertEqual(len(list(json)), 0)
        # Try deleting a nonexistent field
        self.assertRaises(AttributeError, json.__delattr__, 'fake')

    def test_delattr_idempotency(self):
        json = self.F()
        del json.test
        self.assertEqual(json.test, None)

        # Make sure deleting a normal attribute works
        json.foo = 9
        del json.foo
        self.assertRaises(AttributeError, json.__delattr__, 'foo')

        # Check idempotency
        del json.test
        self.assertEqual(json.test, None)

    def test_ordered_fields(self):
        class MyForm(Json):
            strawberry = StringField()
            banana = StringField()
            kiwi = StringField()

        self.assertEqual([x.name for x in MyForm()], ['strawberry', 'banana', 'kiwi'])
        MyForm.apple = StringField()
        self.assertEqual([x.name for x in MyForm()], ['strawberry', 'banana', 'kiwi', 'apple'])
        del MyForm.banana
        self.assertEqual([x.name for x in MyForm()], ['strawberry', 'kiwi', 'apple'])
        MyForm.strawberry = StringField()
        self.assertEqual([x.name for x in MyForm()], ['kiwi', 'apple', 'strawberry'])
        # Ensure sort is stable: two fields with the same creation counter
        # should be subsequently sorted by name.
        MyForm.cherry = MyForm.kiwi
        self.assertEqual([x.name for x in MyForm()], ['cherry', 'kiwi', 'apple', 'strawberry'])

    def test_data_arg(self):
        data = {'test': 'foo'}
        json = self.F(data=data)
        self.assertEqual(json.test.data, 'foo')
        json = self.F(data=data, test='bar')
        self.assertEqual(json.test.data, 'bar')

    def test_empty_formdata(self):
        """"If formdata is empty, field.process_formdata should still run to handle empty data."""

        self.assertEqual(self.F({'other': 'other'}).test.data, '')
        self.assertEqual(self.F({}).test.data, '')


class MetaTest(TestCase):
    class F(Json):
        class Meta:
            foo = 9

        test = StringField()

    class G(Json):
        class Meta:
            foo = 12
            bar = 8

    class H(F, G):
        class Meta:
            quux = 42

    class I(F, G):
        pass

    def test_basic(self):
        form = self.H()
        meta = form.meta
        self.assertEqual(meta.foo, 9)
        self.assertEqual(meta.bar, 8)
        assert isinstance(meta, self.F.Meta)
        assert isinstance(meta, self.G.Meta)
        self.assertEqual(type(meta).__bases__, (
            self.H.Meta,
            self.F.Meta,
            self.G.Meta,
            DefaultMeta
        ))

    def test_missing_diamond(self):
        meta = self.I().meta
        self.assertEqual(type(meta).__bases__, (
            self.F.Meta,
            self.G.Meta,
            DefaultMeta
        ))
