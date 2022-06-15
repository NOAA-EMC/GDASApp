#!/bin/bash

test_file () {
    if test -f "$1"; then
        echo " - $1 exists"
    else
        echo " - $1 does not exist"
        exit 1
    fi
}
