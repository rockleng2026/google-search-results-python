from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name='google-search-no-api',
    version='1.0.0',
    description='Google Search without API Key - Powered by DuckDuckGo',
    author='Your Name',
    url='https://github.com/yourname/google-search',
    packages=find_packages(),
    python_requires='>=3.7',
    install_requires=[
        'requests>=2.25.0',
        'beautifulsoup4>=4.9.0',
        'lxml>=4.6.0',
    ],
    entry_points={
        'console_scripts': [
            'google-search=google_search:run',
        ],
    },
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)