import subprocess
import sys

from setuptools import Command, setup


class RunTests(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        errno = subprocess.call([sys.executable, '-m', 'unittest', 'gis_metadata.tests.tests'])
        raise SystemExit(errno)


with open('README.md') as readme:
    long_description = readme.read()


setup(
    name='gis-metadata-parser',
    description='Parser for GIS metadata standards including ArcGIS FGDC and ISO-19115',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords='arcgis,fgdc,iso,ISO-19115,ISO-19139,gis,metadata,parser,xml,gis_metadata,gis_metadata_parser',
    version='2.0.1',
    packages=['gis_metadata'],
    install_requires=[
        'frozendict>=2.0', 'parserutils>=2.0.1'
    ],
    tests_require=['mock'],
    url='https://github.com/consbio/gis-metadata-parser',
    license='BSD',
    cmdclass={'test': RunTests}
)
