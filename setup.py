from setuptools import setup, find_packages
import os

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name='TLTools',
      version='0.7.0',
      description='Tools for acquiring and processing Ultrasonic NDT data',
      author='Timothy Lardner',
      author_email='timlardner@gmail.com',
      url='https://github.com/timlardner',
      license = "MIT",
      packages=['TLTools'],
      install_requires=[
          'pycuda','matplotlib','numpy','viscm','scipy'
      ],
      long_description='This is a test of TFM awesomeness',
      package_data={'': ['TFMKernel.cu']},
      classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
    ],
     )
