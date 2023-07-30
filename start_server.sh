#!/bin/bash

set -e

export FLASK_APP=main
export FLASK_ENV=development
export FLASK_DEBUG=0
flask run --host=0.0.0.0
