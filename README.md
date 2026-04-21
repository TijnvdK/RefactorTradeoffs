# Master Thesis - Framework

[![GitHub license](https://badgen.net/github/license/Naereen/Strapdown.js)](https://github.com/ThijsJ04/MasterThesis/blob/main/LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-31213/)

_This repository is created and validated on Ubuntu 24.04 LTS with Python 3.12._

## Project Structure

### Static Analysis

Located under `static_analysis/`. This module performs static analysis of PHP codebases and consists of an analyzer and a parser. Given the location of the PHP codebase, the analyzer will set up a Docker environment and execute [PHP Depend](https://pdepend.org/), [PHP_CodeSniffer](https://github.com/squizlabs/php_codesniffer), [PHPMD](https://phpmd.org/), and [PhpMetrics](https://www.phpmetrics.org/). The results are stored in the local `static_analysis/outputs/raw_output` directory. The parser can then be used to parse the raw output into the following CSV format:

```
file_path,method_name,start_line,end_line,cc,mi,halstead_difficulty,amount_of_phpmd_violations,phpmd_violations
```

and stored in the `static_analysis/outputs/parsed_output` directory. The current main function of the parser uses only PHP Depend and PHPMD results.


### Workload Profile

Located under `workload_profile/`. This module is set up to find out how often each function is called in a PHP codebase. The `README.md` file in this directory explains how to set up Xdebug and execute the PHP codebase with the correct Xdebug configuration to generate the correct Xdebug trace. The accompanying `parse_xdebug_trace.py` file can then be used to parse the Xdebug trace into JSONL format, which is stored in the `workload_profile/outputs` directory. The JSONL format shows how often each function is called:

```
{"count": 1, "function_name": "function_name"}
```

### LLM Interaction

Located under `llm_interaction/`. This module is set up to call Ollama language models with different prompt engineering techniques (PETs). The currently supported PETs are prefix/suffix, RCI, and zero-shot CoT. Abstract classes are provided for both provider handlers and PETs, so the user can easily implement new language model providers and PETs.

## Developer setup

- Setup virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

- Setup pre-commit hooks:

```bash
pre-commit install
```

- Execute pytest:

```bash
pytest
```
