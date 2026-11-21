# Tests

Run the repository checks from the project root:

~~~bash
python -m compileall -q raspberry_pi llm_advisory pcb_engine_kit tests
python -m unittest discover -s tests -v
~~~

The supplementary folder-worker tests are run from its directory:

~~~bash
cd pcb_engine_kit
python -m unittest -v test_contracts.py
~~~

The tests cover the IR station state changes, class order, event schema, advisory prompt and response shape, dashboard JavaScript and element IDs, dataset manifest validation, ZIP extraction and image queue handling.

GitHub Actions runs the same checks on pushes and pull requests to main. These are software tests. They do not prove that the camera, GPIO wiring, LED driver, trained detector or Llama model work on the physical Raspberry Pi. Use docs/PI5_COMMISSIONING.md for those checks.
