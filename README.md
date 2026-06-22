# Master Thesis - Framework

[![GitHub license](https://badgen.net/github/license/Naereen/Strapdown.js)](https://github.com/ThijsJ04/MasterThesis/blob/main/LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-31213/)

_This repository is created and validated on Ubuntu 24.04 LTS with Python 3.12._

This repository describes the evaluation framework used for my master thesis. The evaluation framework quantifies and compares standard LLM pipelines and autonomous AI agents across both passive and active refactoring tasks within real-world repositories. Our framework evaluates these approaches on the dual objectives of code correctness and energy efficiency.

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
