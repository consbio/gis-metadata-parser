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
    keywords='fgdc,iso,ISO-19115,ISO-19139,metadata,xml,parser',
    version='0.4.0',
    packages=[
        'gis_metadata', 'gis_metadata.tests'
    ],
    install_requires=[
        'parserutils', 'six'
    ],
    url='https://github.com/consbio/gis_metadata_parser',
    license='BSD',
    cmdclass={'test': RunTests}
)
