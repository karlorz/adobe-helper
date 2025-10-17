"""Setup configuration for futunn-helper package."""

import os

from setuptools import find_packages, setup


def read(fname):
    """Read file contents"""
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="futunn-helper",
    version="0.1.0",
    author="Futunn Helper Contributors",
    description="Asynchronous Python client for Futunn stock market quote API",
    long_description=read("README.md") if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    url="https://github.com/karlorz/futunn-helper",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.7",
    install_requires=[
        "httpx>=0.27.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-asyncio>=0.23.0",
            "black>=24.0.0",
            "flake8>=7.0.0",
        ],
        "validation": [
            "pydantic>=2.0.0",
        ],
    },
    keywords="futunn stock market api async httpx finance trading",
    project_urls={
        "Bug Reports": "https://github.com/karlorz/futunn-helper/issues",
        "Source": "https://github.com/karlorz/futunn-helper",
        "Documentation": "https://github.com/karlorz/futunn-helper/blob/main/README.md",
    },
)
