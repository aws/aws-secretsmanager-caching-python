## AWS Secrets Manager Python caching client

[![Build](https://github.com/aws/aws-secretsmanager-caching-python/actions/workflows/python-package.yml/badge.svg?event=push)](https://github.com/aws/aws-secretsmanager-caching-python/actions/workflows/python-package.yml)
[![codecov](https://codecov.io/github/aws/aws-secretsmanager-caching-python/branch/master/graph/badge.svg?token=DkTHUP8lv5)](https://codecov.io/github/aws/aws-secretsmanager-caching-python)

The AWS Secrets Manager Python caching client enables in-process caching of secrets for Python applications.

## Getting Started

### Required Prerequisites

To use this client you must have:

* Python 3.7 or newer.  Use of Python versions 3.6 or older are not supported.
* An Amazon Web Services (AWS) account to access secrets stored in AWS Secrets Manager.
  * **To create an AWS account**, go to [Sign In or Create an AWS Account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) and then choose **I am a new user.** Follow the instructions to create an AWS account.

  * **To create a secret in AWS Secrets Manager**, go to [Creating Secrets](https://docs.aws.amazon.com/secretsmanager/latest/userguide/manage_create-basic-secret.html) and follow the instructions on that page.

  * This library makes use of botocore, the low-level core functionality of the boto3 SDK.  For more information on boto3 and botocore, please review the [AWS SDK for Python](https://aws.amazon.com/sdk-for-python/) and [Botocore](https://botocore.amazonaws.com/v1/documentation/api/latest/index.html) documentation. 

### Dependencies
This library requires the following standard dependencies:
* botocore
* setuptools_scm
* setuptools

For development and testing purposes, this library requires the following additional dependencies:
* pytest
* pytest-cov
* pytest-sugar
* codecov
* pylint
* sphinx
* flake8
* tox

Please review the `requirements.txt` and `dev-requirements.txt` file for specific version requirements.

### Installation
Installing the latest release via **pip**:
```bash
$ pip install aws-secretsmanager-caching
```

Installing the latest development release:
```bash
$ git clone https://github.com/aws/aws-secretsmanager-caching-python.git
$ cd aws-secretsmanager-caching-python
$ python setup.py install
```

### Development
#### Getting Started
Assuming that you have Python and virtualenv installed, set up your environment and install the required dependencies like this instead of the `pip install aws_secretsmanager_caching` defined above:

```bash
$ git clone https://github.com/aws/aws-secretsmanager-caching-python.git
$ cd aws-secretsmanager-caching-python
$ virtualenv venv
...
$ . venv/bin/activate
$ pip install -r requirements.txt -r dev-requirements.txt
$ pip install -e .
```

#### Running Tests
You can run tests in all supported Python versions using tox. By default, it will run all of the unit and integration tests, but you can also specify your own arguments to past to `pytest`.
```bash
$ tox # runs integ/unit tests, flake8 tests and pylint tests
$ tox -- test/unit/test_decorators.py # runs specific test file
$ tox -e py37 -- test/integ/ # runs specific test directory
```

#### Documentation
You can locally-generate the Sphinx-based documentation via:
```bash
$ tox -e docs
```
Which will subsequently be viewable at `file://${CLONE_DIR}/.tox/docs_out/index.html`

### Usage
Using the client consists of the following steps:
1.  Instantiate the client while optionally passing in a `SecretCacheConfig()` object to the `config` parameter.  You can also pass in an existing `botocore.client.BaseClient` client to the client parameter.
2.  Request the secret from the client instance.
```python
import botocore
import botocore.session
from aws_secretsmanager_caching import SecretCache, SecretCacheConfig

client = botocore.session.get_session().create_client('secretsmanager')
cache_config = SecretCacheConfig() # See below for defaults
cache = SecretCache(config=cache_config, client=client)

secret = cache.get_secret_string('mysecret')
```

#### Cache Configuration
You can configure the cache config object with the following parameters:
* `max_cache_size` - The maximum number of secrets to cache.  The default value is `1024`.
* `exception_retry_delay_base` - The number of seconds to wait after an exception is encountered and before retrying the request.  The default value is `1`.
* `exception_retry_growth_factor` - The growth factor to use for calculating the wait time between retries of failed requests.  The default value is `2`.
* `exception_retry_delay_max` - The maximum amount of time in seconds to wait between failed requests.  The default value is `3600`.
* `default_version_stage` - The default version stage to request.  The default value is `'AWSCURRENT'`
* `secret_refresh_interval` - The number of seconds to wait between refreshing cached secret information.  The default value is `3600.0`.
* `secret_cache_hook` - An implementation of the SecretCacheHook abstract class.  The default value is `None`.

#### Decorators
The library also includes several decorator functions to wrap existing function calls with SecretString-based secrets:
* `@InjectedKeywordedSecretString` - This decorator expects the secret id and cache as the first and second arguments, with subsequent arguments mapping a parameter key from the function that is being wrapped to a key in the secret.  The secret being retrieved from the cache must contain a SecretString and that string must be JSON-based.
* `@InjectSecretString` - This decorator also expects the secret id and cache as the first and second arguments.  However, this decorator simply returns the result of the cache lookup directly to the first argument of the wrapped function.  The secret does not need to be JSON-based but it must contain a SecretString.
```python
from aws_secretsmanager_caching import SecretCache
from aws_secretsmanager_caching import InjectKeywordedSecretString, InjectSecretString

cache = SecretCache()

@InjectKeywordedSecretString(secret_id='mysecret', cache=cache, func_username='username', func_password='password')
def function_to_be_decorated(func_username, func_password):
    print('Something cool is being done with the func_username and func_password arguments here')
    ...

@InjectSecretString('mysimplesecret', cache)
def function_to_be_decorated(arg1, arg2, arg3):
    # arg1 contains the cache lookup result of the 'mysimplesecret' secret.
    # arg2 and arg3, in this example, must still be passed when calling function_to_be_decorated().
```

## Getting Help
We use GitHub issues for tracking bugs and caching library feature requests and have limited bandwidth to address them. Please use these community resources for getting help:
* Ask a question on [Stack Overflow](https://stackoverflow.com/) and tag it with [aws-secrets-manager](https://stackoverflow.com/questions/tagged/aws-secrets-manager).
* Open a support ticket with [AWS Support](https://console.aws.amazon.com/support/home#/)
* if it turns out that you may have found a bug, please [open an issue](https://github.com/aws/aws-secretsmanager-caching-python/issues/new). 
## License

This library is licensed under the Apache 2.0 License. 
