#!/bin/bash

export PYTHONDONTWRITEBYTECODE=1
coverage run -m unittest discover

coverage report -m Code/*.py
