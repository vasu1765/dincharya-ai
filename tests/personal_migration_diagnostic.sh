# Source from the supervised runner after defining its scoped sql function.
run_personal_migration() {
  local file=$1 name=${1##*/} details rc
  [[ $name =~ ^[0-9]{4}_[a-z0-9_]+\.sql$ ]] || return 2
  # -f - gives psql an input line; verbose diagnostics include SQLSTATE.
  # Only allowlisted fields leave the pipe. Discard SQL, values and context.
  if details=$(set -o pipefail
    sql -v VERBOSITY=verbose -f - < "$file" 2>&1 >/dev/null |
      LC_ALL=C awk '
        /^psql:<stdin>:[0-9]+: (ERROR|FATAL|PANIC):  [0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z]:/ && !state {
          split($1, prefix, ":"); line=prefix[3]; state=substr($3,1,5)
        }
        /^LINE [0-9]+:/ && state && !relative { relative=$2; sub(/:.*/, "", relative) }
        END { printf "sqlstate=%s input_line=%s statement_line=%s", state?state:"unknown",
                     line?line:"unknown", relative?relative:"unknown" }
      '
  ); then
    return 0
  else
    rc=$?
    printf 'FAIL migration=%s exit=%d %s\n' "$name" "$rc" "$details" >&2
    return "$rc"
  fi
}
