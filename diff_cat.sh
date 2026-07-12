#!/bin/bash

#
while IFS= read -r line; do

    status="${line:0:2}"
    file="${line:3}"

    case "$status" in

        " M"|"M ")
			echo "clear; git diff \"$file\""
			echo ""
            ;;

        "??")

            if [ -f "$file" ]; then
                echo "clear; cat \"$file\""

            elif [ -d "$file" ]; then
                echo "clear; lt -R \"$file\""

            else
                echo "# Ignorado: $file"
            fi
            ;;

    esac

done < <(git status --porcelain)
