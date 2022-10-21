import json
import setuptools

with open("template/README.md", "r") as fh:
    long_description = fh.read()

with open('requirements.txt') as fr:
    requirements = fr.read().strip().split('\n')

with open('metadata.json') as fr:
    metadata = json.load(fr)

setuptools.setup(
    name="gryphon-routing-here-maps",  # Name of the repository
    version="0.0.3",
    author=metadata.get("author", ""),
    author_email=metadata.get("author_email", ""),
    description=metadata.get("description", ""),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://owlabs.atlassian.net/wiki/spaces/MappingAssets/overview",  # Repository URL or externally maintained page
    packages=setuptools.find_packages(),
    python_requires='>=3.7',
    install_requires=requirements,
)
