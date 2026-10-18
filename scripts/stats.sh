#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! -f "$1" ]]; then
  echo "Использование: $0 путь/к/connections.csv" >&2
  exit 1
fi

file=$1
echo "Строк данных: $(( $(wc -l < "$file") - 1 ))"
echo "Распределение классов:"
tail -n +2 "$file" | cut -d, -f15 | sort | uniq -c
