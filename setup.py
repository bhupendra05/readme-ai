from setuptools import setup, find_packages

setup(
    name="readme-ai",
    version="0.1.0",
    description="AI-powered GitHub README generator — analyzes your repo and writes the README for you",
    author="bhupendra05",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "click>=8.1",
        "rich>=13.0",
        "python-dotenv>=1.0",
        "pyyaml>=6.0",
        "requests>=2.31",
    ],
    extras_require={
        "openai": ["openai>=1.0"],
        "anthropic": ["anthropic>=0.25"],
        "all": ["openai>=1.0", "anthropic>=0.25"],
    },
    entry_points={
        "console_scripts": [
            "readme-ai=readme_ai.cli:main",
        ]
    },
)
