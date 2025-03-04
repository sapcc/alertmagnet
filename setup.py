from setuptools import setup, find_packages

setup(
    name="main",
    version="0.1.0",
    packages=find_packages(),
    py_modules=["main"],
    install_requires=[
        "pandas",
        "prometheus-client",
        "requests",
    ],
)
