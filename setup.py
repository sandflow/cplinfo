import pathlib
from setuptools import setup, find_packages

here = pathlib.Path(__file__).parent.resolve()

long_description = (here / 'README.md').read_text(encoding='utf-8')

setup(
    name='cplinfo', 
    version='1.0.0b1',
    description='Extracts Composition information from an IMF CPL document',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/sandflow/cplinfo',
    author='Sandflow Consulting LLC',
    author_email='info@sandflow.com',
    keywords="cpl imf composition",

    package_dir={'cplinfo': 'src/main/python/cplinfo'}, 

    packages=find_packages(where='src/main/python'),

    python_requires='>=3.7, <4',

    project_urls={
        'Bug Reports': 'https://github.com/sandflow/cplinfo/issues',
        'Source': 'https://github.com/sandflow/cplinfo',
    },

    entry_points={
        "console_scripts": [
            "tt = cplinfo.cli:main"
        ]
    },
)
