#!/bin/bash

# quit on errors:
set -o errexit

# quit on unbound symbols:
set -o nounset

# remove topical branch
join_by(){
  local d=$1; shift; echo -n "$1"; shift; printf "%s" "${@/#/$d}";
}
remove_topical(){
  FILE_TO_FILTER=$1
  TOPICALS=`grep ^-e requirements.topical.branches.txt |awk -F"=" '{print $2}'`
  TO_FILTER=`join_by '\|' $TOPICALS`
  grep -v $TO_FILTER $1
}

remove_topical requirements.pinned.txt > .ci-pinned-requirements.txt
cat requirements.topical.branches.txt >> .ci-pinned-requirements.txt
