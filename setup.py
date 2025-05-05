import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

with open('standards-requirements.txt') as f:
    standards_requirements = f.read().splitlines()

setuptools.setup(
    name="honeybee-openstudio",
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    author="Ladybug Tools",
    author_email="info@ladybug.tools",
    description="Honeybee extension for translating HBJSON models to OpenStudio (for OSM, IDF and gbXML).",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ladybug-tools/honeybee-openstudio",
    packages=setuptools.find_packages(exclude=["tests*", "equest_docs*"]),
    install_requires=requirements,
    extras_require={
        'standards': standards_requirements
    },
    include_package_data=True,
    entry_points={
        "console_scripts": ["honeybee-openstudio = honeybee_openstudio.cli:openstudio"]
    },
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent"
    ],
    license="AGPL-3.0"
)
