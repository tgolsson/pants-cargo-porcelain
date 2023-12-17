#!/usr/bin/env bash

output=$(examples.python-package.src.python_package/pex.pex)
expected_output="Finished importing Rust module
Hello, world!
Finished running Rust module"
if [[ "$output" == "$expected_output" ]]; then
  echo "Test passed!"
  exit 0
else
  echo "Test failed!"
  echo "Expected output: <<"
  printf "$expected_output"
  echo "<<"
  echo "Actual output: <<"
  printf "$output"
  echo "<<"


  exit 1
fi
```
