from setuptools import setup, find_packages
import os

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name='TLTools',
      version='2.0.5',
      description='Tools for acquiring and processing Ultrasonic NDT data',
      author='Timothy Lardner',
      author_email='timlardner@gmail.com',
      url='https://github.com/timlardner',
      license = "Not to be used by anyone",
      packages=['TLTools'],
      install_requires=[
          'pycuda','matplotlib','numpy','viscm','scipy','pillow','pythonnet',
      ],
      long_description='This is a test of TFM awesomeness',
      package_data={'': ['TFMKernel.cu']},
      classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Topic :: Utilities",
        "License :: Other/Proprietary License",
        "Intended Audience :: Developers",
    ],
     )
