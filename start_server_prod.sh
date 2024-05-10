#!/bin/sh

set -e

gunicorn main:app -b 0.0.0.0:8000
