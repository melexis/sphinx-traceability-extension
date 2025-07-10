# -*- coding: utf-8 -*-

from css_html_js_minify import process_single_js_file
from setuptools import setup, find_namespace_packages

from setuptools_scm import get_version
version = get_version()

project_url = 'https://github.com/melexis/sphinx-traceability-extension'

requires = [
    'Sphinx>=7.4,<9.0',
    'sphinxcontrib-jquery>=2.0.0,!=3.0.0',
    'docutils',
    'matplotlib<4.0',
    'natsort',
    'python-decouple',
    'requests',
]
js_file_path = 'mlx/traceability/assets/traceability.js'
process_single_js_file(js_file_path, output_path=js_file_path.replace('.js', f'-{version}.min.js'))

setup(
    name='mlx.traceability',
    dynamic="version",
    url=project_url,
    license='GPL-3.0',
    author='Melexis',
    author_email='jce@melexis.com',
    description='Sphinx traceability extension (Melexis fork)',
    long_description=open("README.md").read(),
    long_description_content_type='text/markdown',
    project_urls={
        'Documentation': 'https://melexis.github.io/sphinx-traceability-extension',
        'Source': 'https://github.com/melexis/sphinx-traceability-extension',
        'Tracker': 'https://github.com/melexis/sphinx-traceability-extension/issues',
    },
    zip_safe=False,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Framework :: Sphinx :: Extension',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Documentation',
        'Topic :: Documentation :: Sphinx',
        'Topic :: Utilities',
    ],
    platforms='any',
    packages=find_namespace_packages(where=".", exclude=("doc.*", "doc", "tests.*", "tests", "build*")),
    package_dir={"": "."},
    python_requires='>=3.8',
    include_package_data=True,
    install_requires=requires,
    keywords=[
        'traceability',
        'requirements engineering',
        'requirements management',
        'software engineering',
        'systems engineering',
        'sphinx',
        'requirements',
        'ASPICE',
        'ISO26262',
        'ASIL',
    ],
    package_data={'mlx.traceability': ['assets/traceability-*.js']},
)
