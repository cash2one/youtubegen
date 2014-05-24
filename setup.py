#!/usr/bin/env python

from setuptools import setup

setup(name='youtubegen',
      version='0.9',
      description='Generate and upload YouTube music videos',
      license='GPL',
      keywords='youtube music video',
      author='Daniel da Silva',
      author_email='var.mail.daniel@gmail.com',
      url='https://github.com/ddasilva/youtubegen',
      packages=['youtubegen'],
      install_requires=['Pillow', 'gdata'],
      entry_points={
          'console_scripts': [
              'youtubegen = youtubegen:main'
          ]
      },
)

