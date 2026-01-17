#!/usr/bin/env bash
set -e

echo "🔧 Restoring all '# REMOVED:' blocks"

FILES=$(grep -R "# REMOVED:" -l app/)

for file in $FILES; do
  echo "➡️ Restoring $file"
  sed -i 's/^# REMOVED: //g' "$file"
done

echo "✅ Restore complete"
