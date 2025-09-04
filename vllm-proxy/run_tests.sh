#!/bin/bash

. .venv/bin/activate
PYTHONPATH=src python -m pytest tests/ -v "$@"