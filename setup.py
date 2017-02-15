from setuptools import setup, find_packages
import os

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name='CUETools',
      version='0.3.5',
      description='Tools for processing Ultrasonic NDT data',
      author='Timothy Lardner',
      author_email='timlardner@gmail.com',
      url='https://github.com/timlardner',
      license = "MIT",
      packages=['CUETools'],
      install_requires=[
          'pycuda','matplotlib','numpy'
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
