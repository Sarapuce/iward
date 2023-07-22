#!/bin/bash

set -e

export FLASK_APP=main
export FLASK_ENV=development
flask run
