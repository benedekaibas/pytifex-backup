# About

This repository contains the required files to showcase **Pytifex**.
This repository includes the Pytifex source code, generated outputs, and the full environment configuration used to produce the results.

## Experimental Setup

I conducted all experiments on a workstation running Ubuntu 24.04.3 LTS, equipped with a 13th Gen Intel® Core™ i7-1355U (12 cores) and 16 GB RAM. Our implementation uses Python 3.12.9. The code examples were evaluated using the following versions: `mypy 1.19.0 (compiled: yes)`, `pyrefly 0.44.2`, `zuban 0.3.0`, and `ty 0.0.1-alpha.32`.

## Where to Find What

I provide where are all the files that were asked to produce.

### An example of a Python function where the four type checkers would disagree on the outcome

I have two examples for this task since they better display the meaning of my tool.

`src/tc_disagreement/disagreement.py`

This file contains a false negative produced by `ty` while other type checkers (`mypy`, `pyrefly`, `zuban`) correctly analyzed the code example.

`src/tc_disagreement/only_mypy_correct.py`

Very strong example where only `mypy` gives a false analysis while all the other type checkers produce a `false negative` including `pyrefly`,
`zuban`, and `ty`. This is a serious issue since the mentioned type checkers do not detect the bug. By providing this example to the developing
teams of these type checkers would be a significant contribution to make them safer (produce less false reports).

These are the two examples that I have included in this demo.

## Setup
