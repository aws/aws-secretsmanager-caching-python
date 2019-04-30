from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="aws_secretsmanager_caching",
    description="Client-side AWS Secrets Manager caching library",
    url="https://github.com/aws/aws-secretsmanager-caching-python",
    author="Amazon Web Services",
    author_email="aws-secretsmanager-dev@amazon.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(where="src", exclude=("test",)),
    package_dir={"": "src"},
    classifiers=[
        'Development Status :: 5 - Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved ::  Apache License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'
    ],
    keywords='secretsmanager secrets manager development cache caching client',
    use_scm_version={
        'write_to': 'version.txt'
    },
    python_requires='>3.5',
    install_requires=['botocore', 'setuptools_scm'],
    setup_requires=['pytest-runner', 'setuptools-scm'],
    tests_require=['pytest', 'pytest-cov', 'pytest-sugar', 'codecov']

)
