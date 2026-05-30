"""Setup for google-ads-cli — CLI harness for the Google Ads API."""

from setuptools import setup, find_namespace_packages

setup(
    name="google-ads-cli",
    version="1.0.0",
    description="CLI harness for the Google Ads API (google-ads-python)",
    long_description=open("cli_anything/google_ads/README.md").read(),
    long_description_content_type="text/markdown",
    author="Google Ads CLI Contributors",
    license="Apache-2.0",
    python_requires=">=3.9",
    # PEP 420 namespace package: cli_anything/ has NO __init__.py
    packages=find_namespace_packages(include=["cli_anything.*"]),
    package_data={
        "cli_anything.google_ads": ["skills/*.md"],
    },
    install_requires=[
        "google-ads>=24.0.0",
        "click>=8.0.0",
        "PyYAML>=5.1",
        "google-auth-oauthlib>=1.0.0",
        "prompt_toolkit>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-mock>=3.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "google-ads-cli=cli_anything.google_ads.google_ads_cli:main",
            "cli-anything-google-ads=cli_anything.google_ads.google_ads_cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP",
    ],
)
