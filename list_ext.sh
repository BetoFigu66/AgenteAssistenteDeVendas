#!/bin/bash

find . -type f \
| sed 's|.*\.||' \
| sort \
| uniq -c \
| sort -nr
