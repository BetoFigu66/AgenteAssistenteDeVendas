#!/bin/bash

git status --porcelain | while IFS= read -r line; do
    status="${line:0:2}"
    file="${line:3}"

    case "$status" in
        " D"|"D ")
            echo "git add \"$file\" # deleted"
            ;;
        " M"|"M ")
            echo "clear; git diff --ws-error-highlight=all \"$file\""
            ;;
        "??")
            if [ -f "$file" ]; then
                echo "clear; cat \"$file\""
            elif [ -d "$file" ]; then
                echo "clear; lt \"$file\""
            fi
            ;;
    esac
done