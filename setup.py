from setuptools import setup

setup(
   name='ham_file',
   version='0.1',
   description="Read & write proprietery .ham files",
   author='Tatrabbit',
   author_email='alx1213@gmail.com',
   packages=['ham_file'],
   install_requires=['regex'], # external packages as dependencies
)