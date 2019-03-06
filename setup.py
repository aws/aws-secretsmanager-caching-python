from setuptools import setup, find_packages

setup(
    name="aws_secretsmanager_caching",
    description="Client-side AWS Secrets Manager caching library",
    url="https://aws.amazon.com/secrets-manager/",
    author="Amazon Web Services",
    author_email="aws-secretsmanager-dev@amazon.com",
    version="1.0",
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
    python_requires='>3.5',
    setup_requires=['pytest-runner'],
    tests_require=['pytest<3.8.0', 'pytest-cov', 'pytest-sugar', 'codecov>=1.4.0']

)
