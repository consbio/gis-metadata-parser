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
        errno = subprocess.call([sys.executable, '-m',  'unittest', 'gis_metadata.xml.tests.tests'])
        if errno == 0:
            errno = subprocess.call([sys.executable, '-m',  'unittest', 'gis_metadata.metadata.tests.tests'])
        raise SystemExit(errno)


setup(
    name='gis-metadata-parser',
    description='Parser for GIS metadata standards including FGDC and ISO-19115',
    keywords='fgdc,iso,ISO-19115,metadata,xml,parser',
    version='0.1.0',
    packages=[
        'gis_metadata', 'gis_metadata.metadata', 'gis_metadata.xml',
        'gis_metadata.metadata.tests', 'gis_metadata.xml.tests'
    ],
    install_requires=[
        'defusedxml'
    ],
    url='https://github.com/consbio/gis-metadata-parser',
    license='BSD',
    cmdclass={'test': RunTests}
)