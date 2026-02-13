from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

def parse_requirements(filename):
    with open(filename, "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

requirements = parse_requirements("requirements.txt")

setup(
    name="promptfish",
    version="0.1.0",
    author="Lizrd",
    description="Random writing prompts from your epub collection",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "promptfish=promptfish.main:main",
        ],
    },
    python_requires=">=3.8",
)
