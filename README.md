# RefactorTradeoffs

[![GitHub license](https://badgen.net/github/license/Naereen/Strapdown.js)](https://github.com/ThijsJ04/MasterThesis/blob/main/LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-31213/)

_This repository is created and validated on Ubuntu 24.04 LTS with Python 3.12._

## Overview

This repository describes an evaluation framework created for support for my master thesis. The evaluation framework enables both generative AI and LLM-based agents to perform active and passive refactoring on a code repository while measuring inference costs.

Next to the framework, the repository also contains a set of analysis notebooks to visualize the trade-offs between inference costs and refactoring outputs.

For passive refactoring, the break-even point (BEP) is determined. BEP is defined as the number of time units required for the cumulative energy savings of the optimized repository to outweigh the energy costs of the refactoring process. If we define $e_\text{orig}$ as the energy consumed by the non-refactored repository in $x$ time units, $e_\text{opt}$ as the energy consumed by the refactored repository in $x$ time units, and $E_\text{optim}$ as the energy consumed during the refactoring process, the BEP can be computed as:

$$\text{BEP}=\frac{E_\text{optim}}{e_\text{orig}-e_\text{opt}}$$

To compute the BEP, the energy consumption of the original and refactored repository must be measured over a period of time. You can make use of the tools within the repository that are able to measure the energy of the CPU with RAPL or CPU utilization and the GPU with NVIDIA's NVML. But the measuring is not included in the framework.

For active refactoring, the relative debt effort estimate is put into relation with the computional cost of resolving that debt. The technical debt and their effort estimates are retrieved with SonarQube. Retrieving this for both the original and refactored repository are outside the scope of this framework.

## Requirements

- Python 3.12
- A CPU which supports the `power/energy-pkg/` RAPL event.
- A NVIDIA GPU which is a Volta or newer.

## Project setup

- Setup environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install and pull git-lfs files
git lfs install
git lfs pull

# Pull cloud-energy submodule
git submodule update --init --recursive

# Setup pre-commit hooks:
pre-commit install
```

- Create a `.env` file:

```bash
cp .env.example .env
# Edit the .env file to set the required environment variables.
```

- To execute the included pytests, execute:

```bash
pytest
```

## Initializing a Repository to Refactor

The framework is repository (and therefore programming language) agnostic. To make this possible, each repository has to be registered with the minimum amount of information to enable the framework to perform refactoring. This is done by creating a file under `src/pipeline/repository_registry/repositories`. This file must call the `register_repository` function with the following parameters:

- language_name: Human-readable name of the programming language.
- language_extension: The file extension of the programming language. Only files with this extension will be refactored.
- syntax_check: A function with signature `def X(str) -> Tuple[bool, str]` that can verify the syntax of a file for the programming language.
- correctness_check: A function with signature `def X(int | None) -> Tuple[bool, str]` that can verify the correctness of the repository to be refactored. This can, for example, involve the execution of unit tests.
- For passive refactoring, the Tree Sitter language and node types must be provided. With this information functions to be refactored will be extracted from code files.

If you want to perform active refactoring, you need to execute SonarQube on the repository. You can use `src/sonarqube/parse_issues.py` to parse the issues and have it store them automatically in the format the framework expects. The parsed issues need to be stored at `src/sonarqube/sonarqube_issues.json`.

## Experiment Configurations

The user must provide the ID of the registered repository via the framework's configuration file (`src/config/experiment.yaml`). This configuration file includes, furthermore, a series of other variables. Some of the variables are self-explanatory, while other we will explain in more detail.

- vllm_server_timeout defines the timeout for setting up/creating the vLLM server.
- run_size defines the number of runs to be performed. A ``run'' includes defining the units to be refactored and the refactoring of these defined units. Each run starts from the same fresh slate, i.e., the target code repository before refactorings, and does not include any changes made by other runs.
- min_function_loc is used to define the passive refactoring units (see Section~\ref{sec:unit-definition}).
- cooldown_period represents the idle time in seconds between runs.

## Running on a HPC

For my master thesis, I ran the framework on a high-performance computing (HPC) cluster. To make this possible I made use of apptainers for the syntax and correctness checks (stored under `apptainers`), but this might not need to be necessary for all repositories. I also created a starting script (`HPC_starting_script.sh`). This script shows how I set up the environment with the apptainers and expected variables before executing the framework. The script can be used as a template for running the framework on a HPC cluster.

## Performing Analysis

There are a set of notebooks included in the repository under `src/result_analysis`. These notebooks can be used to visualize the trade-offs between inference costs and refactoring outputs.

## License

This project is licensed under the [MIT License](LICENSE).
