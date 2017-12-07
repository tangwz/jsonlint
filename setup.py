import sys
from setuptools import setup

extra = {}

if sys.version_info < (2, 7):
    extra['install_requires'] = ['ordereddict>=1.1']


setup(
    name='jsonlint',
    version='0.1',
    license='BSD',
    url='https://github.com/tangwz/jsonlint',
    author='Tangwz, Thomas Johansson, James Crasta',
    author_email='tangwz.com@gmail.com',
    description='A flexible json validation for python web development.',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    packages=[
        'jsonlint',
    ],
    package_data={
        'jsonlint': ['locale/wtforms.pot', 'locale/*/*/*'],
    },
    test_suite='tests.runtests',
    extras_require={
        'Locale': ['Babel>=1.3'],
        ':python_version=="2.6"': ['ordereddict'],
    },
    **extra
)
