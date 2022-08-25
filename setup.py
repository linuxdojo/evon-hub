from setuptools import setup, find_packages

with open("version.txt") as f:
    version = f.read().strip()

setup(
    name                 = 'evon',
    version              = version,
    long_description     = __doc__,
    packages             = find_packages(),
    include_package_data = True,
    zip_safe             = False,
    entry_points         = {
        'console_scripts': [
            'evon = evon.cli:main',
        ],
    },
)
