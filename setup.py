"""
Setup configuration for AutoGen Enterprise Code Generator.
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="codegen-autogen-davidkeszeg",  # Egyedi név a projektnek
    version="1.0.0",
    author="davidkeszeg",  # A te neved
    author_email="csdavid931017@gmail.com",  # A te e-mail címed
    description="Professional AutoGen-based code generation system with multi-agent architecture",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/davidkeszeg/Code_gen_Autogen", # A te GitHub repód URL-je
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.1.0",
            "mypy>=1.7.0",
            "pre-commit>=3.5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "autogen-enterprise=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "autogen_enterprise": [
            "config/*.yaml",
            "templates/*.jinja2",
        ],
    },
)
