from setuptools import setup

setup(
    name="main",
    version="0.1.0",
    py_modules=["main", "analyzing", "extension", "filtering", "presenting", "querying", "utilities"],
    install_requires=[
        "click",
        "pandas",
        "prometheus-client",
        "requests",
    ],
)
