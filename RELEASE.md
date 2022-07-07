```
~/.pypirc

[pypi]
  username = __token__
  password = pypi-TOKEN_GOES_HERE
```

`rm -r dist/`\
`python3 -m build`\
`python3 -m twine upload dist/*`
