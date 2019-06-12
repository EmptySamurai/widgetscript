#!/usr/bin/env python

from setuptools import setup
from subprocess import check_call
from setuptools.command.build_py import build_py
import shutil


class NPMInstall(build_py):
    def run(self):
        check_call(['npm', 'install', '.'])
        shutil.move("./node_modules", "./widgetscript/node_modules")
        build_py.run(self)


setup(name='widget-script',
      version='0.1',
      description='Python Distribution Utilities',
      author='Nikita Gryaznov (emptysamurai)',
      author_email='nikgryaznov@gmail.com',
      url='https://github.com/EmptySamurai/widgetscript',
      packages=['widgetscript'],
      include_package_data=True,
      package_data={'widgetscript': ["node_modules/*", "node_modules/**/*", "node_modules/**/**/*"]},
      install_requires=[
          "transcrypt",
          "astor"
      ],
      cmdclass={
          'build_py': NPMInstall
      }
      )
