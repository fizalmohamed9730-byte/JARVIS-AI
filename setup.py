"""Setup configuration for JARVIS."""

from setuptools import setup, find_packages
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="jarvis",
    version="1.0.0",
    author="JARVIS Team",
    author_email="team@jarvis.ai",
    description="JARVIS - AI Personal Assistant",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/jarvis",
    packages=find_packages(
        include=["backend", "backend.*", "vision", "vision.*", "notes", "notes.*", "plugins", "plugins.*"]
    ),
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "pydantic>=2.5.0",
        "sqlalchemy>=2.0.0",
        "asyncpg>=0.29.0",
        "alembic>=1.13.0",
        "redis>=5.0.0",
        "aiohttp>=3.9.0",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "python-multipart>=0.0.6",
        "websockets>=12.0",
        "openai>=1.6.0",
        "opencv-python>=4.8.0",
        "numpy>=1.24.0",
        "pytesseract>=0.3.10",
        "Pillow>=10.0.0",
        "python-dotenv>=1.0.0",
        "httpx>=0.25.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=4.1.0",
            "ruff>=0.1.0",
            "black>=23.0.0",
            "mypy>=1.7.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    entry_points={
        "console_scripts": [
            "jarvis=backend.main:main",
        ],
    },
)
