from setuptools import setup, find_packages

setup(
    name="voice-assistant",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "livekit>=1.0.0",
        "livekit-api>=1.0.0",
        "cerebras-cloud-sdk>=0.5.0",
        "python-dotenv>=1.0.0",
        "httpx>=0.24.0",
        "numpy>=1.24.0",
        "sentence-transformers>=2.2.0",
        "cachetools>=5.3.0",
        "scikit-learn>=1.3.0",
        "pydantic>=2.0.0",
    ],
    python_requires=">=3.12",
    author="Your Name",
    author_email="your.email@example.com",
    description="A health-focused AI assistant with voice capabilities",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.12",
    ],
)
