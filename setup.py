from setuptools                 import setup
from setuptools                 import find_packages
from setuptools.command.test    import test as TestCommand

import sys

class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        result = pytest.main(self.test_args)
        sys.exit(result)

name = 'sqlalchemy_traversal'

requires = [
    'setuptools'
    , 'pyramid'
    , 'SQLAlchemy'
    , 'zope.interface'
]

setup(
    name = name
    , version='0.0'
    , url='http://github.com/eventray/' + name
    , author='John Anderson'
    , author_email='sontek@gmail.com'
    , packages=find_packages()
    , include_package_data = True
    , install_requires = requires
    , tests_require = requires + ['pytest', 'mock', 'webtest']
    , zip_safe = False
    , cmdclass = {'test': PyTest}
)
