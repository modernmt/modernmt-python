```
~/.pypirc

[pypi]
  username = __token__
  password = pypi-TOKEN_GOES_HERE
```

```
cd <repo>
pip install virtualenv          # if you don't already have virtualenv installed
virtualenv venv                 # to create your new environment (called 'venv' here)
source venv/bin/activate        # to enter the virtual environment
pip install -r requirements.txt # to install the requirements in the current environment
```

```
rm -r dist/
python -m build
python -m twine upload dist/*
```
