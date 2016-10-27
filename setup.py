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


setup(
    name='gis_metadata_parser',
    description='Parser for GIS metadata standards including FGDC and ISO-19115',
    keywords='arcgis,fgdc,iso,ISO-19115,ISO-19139,gis,metadata,parser,xml,gis_metadata,gis_metadata_parser',
    version='0.9.4',
    packages=[
        'gis_metadata', 'gis_metadata.tests'
    ],
    install_requires=[
        'parserutils', 'six'
    ],
    url='https://github.com/consbio/gis-metadata-parser',
    license='BSD',
    cmdclass={'test': RunTests}
)
