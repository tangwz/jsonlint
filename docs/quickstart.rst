Quickstart
==========

Creating Jsonlints
------------------
Jsonlint provides the highest level API in jsonlint.s. They contain your field definitions, delegate validation,
take input, aggregate errors, and in general function as the glue holding everything together.

To create a form, one makes a subclass of Json and defines the fields declaratively as class attributes::

    from jsonlint import Json

    class MyLint(Json):
        name = StringField(validators=[DataRequired()])

    mylint = MyLint({'name': 'demo'})
    print mylint.validate() # True
    print mylint.name.data  # demo

In-line Validators
------------------
In order to provide custom validation for a single field without needing to write a one-time-use validator,
validation can be defined inline by defining a method with the convention validate_fieldname::

    from jsonlint import Json
    from jsonlint.fields import IntegerField
    from jsonlint.validators import ValidationError


    class AgeLint(Json):
        age = IntegerField()

        def validate_age(form, field):
            if field.data < 13:
                raise ValidationError("We're sorry, you must be 13 or older to register")


    agelint = AgeLint({'age': 12})
    print agelint.validate()  # False
    print agelint.age.errors  # ["We're sorry, you must be 13 or older to register"]

Fields
------
Jsonlint fields delegate to validators for data validation.
Fields fork from `WTForms <https://wtforms.readthedocs.io/en/latest/fields.html>`_ and modify most of fields.
You can use most of Fields like `WTForms <https://wtforms.readthedocs.io/en/latest/fields.html>`_. Except ListField
and ObjectField.

ListField
---------
ListField get json list and validate it. Jsonlint's ListField optimize FieldList of WTForms's weird behavior.
For example::

    from jsonlint import Json
    from jsonlint.fields import StringField, ListField
    from jsonlint.validators import DataRequired, ValidationError

    class ListLint(Json):
        cars = ListField(StringField(validators=[DataRequired()]))

        def validate_cars(form, field):
            if 'BMW' in field.data:
                raise ValidationError("We're sorry, you cannot drive BMW")


    listlint = ListLint({'cars': ['Benz', 'BMW', 'Audi']})
    print listlint.validate()   # False
    print listlint.cars.errors  # ["We're sorry, you cannot drive BMW"]

ObjectField
-----------
ObjectField get json list and validate it. For example::

    from jsonlint import Json
    from jsonlint.fields import ObjectField, IntegerField, BooleanField

    class T(Json):
        status = BooleanField()
        code = IntegerField()

    class DataLint(Json):
        data = ObjectField(T)

    datalint = DataLint({'data': {'status': True, 'code': 200}})
    print datalint.validate()  # False
    print datalint.data.code.data  # 200
