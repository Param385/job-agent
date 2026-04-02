from setuptools import setup, find_packages

setup(
    name="job-agent",
    version="1.0.0",
    description="AI-powered job application automation system",
    author="Job Agent",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.3",
        "sqlalchemy>=2.0.30",
        "openai>=1.30.1",
        "typer>=0.12.3",
        "rich>=13.7.1",
        "python-dotenv>=1.0.1",
        "tenacity>=8.3.0",
        "reportlab>=4.2.0",
        "markdown2>=2.4.13",
        "tabulate>=0.9.0",
    ],
    entry_points={
        "console_scripts": [
            "job-agent=src.cli.main:app",
        ],
    },
)
