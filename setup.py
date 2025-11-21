from __future__ import annotations

from pathlib import Path
from typing import List

from setuptools import find_packages, setup

ROOT = Path(__file__).parent
PACKAGE_DIR = ROOT / "pdf_vision_processor"
VERSION_FILE = PACKAGE_DIR / "_version.py"


def read_version() -> str:
    scope: dict[str, str] = {}
    exec(VERSION_FILE.read_text(encoding="utf-8"), scope)
    return scope["__version__"]


def read_requirements() -> List[str]:
    requirements_path = ROOT / "requirements.txt"
    if not requirements_path.exists():
        return []
    requirements: List[str] = []
    for line in requirements_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        requirements.append(line)
    return requirements


def read_readme() -> str:
    readme_path = ROOT / "README.md"
    return readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""


setup(
    name="pdf-vision-processor",
    version=read_version(),
    description="FastAPI service for LLM-powered PDF analysis",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="PDF Vision Processor Maintainers",
    url="https://github.com/shamitv/pdf_vision_processor/",
    project_urls={
        "Documentation": "https://github.com/shamitv/pdf_vision_processor/",
    },
    license="Apache License 2.0",
    license_files=["LICENSE"],
    python_requires=">=3.10",
    packages=find_packages(exclude=("tests", "docs", "scripts")),
    include_package_data=True,
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0",
            "black>=24.0",
            "mypy>=1.7",
            "twine>=5.0",
            "build>=1.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "pdf-vision-processor=pdf_vision_processor.cli:main",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: FastAPI",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
)
