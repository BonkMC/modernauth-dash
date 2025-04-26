from setuptools import setup, find_packages

setup(
    name="modernauthdash",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages("src"),
    include_package_data=True,
    install_requires=[
        "Flask"
    ]
)
