This is development information for the Shape Analysis Plugin. One big caveat is we are developing on macOS, your mileage will vary if you are using Microsoft Windows. Don't worry, we will provide recipes for that shortly.

# Install

## Python 3.7.x

User needs to have Python 3.7.x installed. It can be [downloaded here][python-download].

Check python version

```
python3 --version
```

We have `Python 3.7.3`


## pip

Install pip

```
python3 -m pip install --user --upgrade pip
```

Check the verison of pip

```
python3 -m pip --version
```

We have `pip 19.3.1 (python 3.7)`

## Python virtual environment

We want to give the user a recipe to install the Shape Analysis Plugin and its dependencies into a Python virtual environment (venv) so we don't contaminate or break their system wide install of Python.

Following [venv instructions][venv]

Install venv

```
python3 -m pip install --user virtualenv
```

We have `virtualenv-16.7.8`

Create a virtual environment. This will create an environment in a folder named `env`

```
cd ShapeAnalysisPlugin
python3 -m venv env
```

Activate the virtual environment

```
cd ShapeAnalysisPlugin
source env/bin/activate
```

Deactivate the virtual environment

```
deactivate
```


## Snapshot of versions we are using

```
Python 3.7.3
pip 19.3.1 (python 3.7)
virtualenv-16.7.8
```


[python-download]: https://www.python.org/downloads/
[venv]: https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/