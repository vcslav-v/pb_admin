from setuptools import setup
import re

with open("loguru/__init__.py", "r") as file:
    regex_version = r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]'
    version = re.search(regex_version, file.read(), re.MULTILINE).group(1)


def get_requirements():
    """Build the requirements list for this project"""
    requirements_list = []

    with open("requirements.txt", 'r') as reqs:
        for install in reqs:
            requirements_list.append(install.strip())

    return requirements_list


setup(
    name='pb_admin',
    version=regex_version,
    description='Admin API for pb project',
    author='Vaclav_V',
    packages=['pb_admin'],
    install_requires=get_requirements(),
)
