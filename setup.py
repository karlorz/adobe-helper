"""Legacy setup configuration for adobe-helper package."""

import os

from setuptools import find_packages, setup


def read(fname):
    """Read file contents"""
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="adobe-helper",
    version="0.1.0",
    author="Adobe Helper Contributors",
    description="Python client for Adobe PDF-to-Word conversion workflows",
    long_description=read("README.md") if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    url="https://github.com/karlorz/adobe-helper",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.11",
    install_requires=[
        "httpx[http2]>=0.27.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-asyncio>=0.23.0",
            "black>=24.0.0",
            "ruff>=0.7.1",
            "mypy>=1.8.0",
        ],
    },
    keywords="adobe pdf conversion httpx async",
    project_urls={
        "Bug Reports": "https://github.com/karlorz/adobe-helper/issues",
        "Source": "https://github.com/karlorz/adobe-helper",
        "Documentation": "https://github.com/karlorz/adobe-helper/blob/main/README.md",
    },
)
