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
remove_devel(){
  FILE_TO_FILTER=$1
  TOPICALS=`grep ^-e requirements.devel.txt |awk -F"=" '{print $2}'`
  TO_FILTER="^`join_by '\|^' $TOPICALS`"
  TO_FILTER2=`echo $TO_FILTER | sed -e 's/\[/\\\[/g'`
  grep -v -e $TO_FILTER2 $1
}

# production env
remove_topical requirements.pinned.txt > .ci-prod-requirements.txt
cat requirements.topical.branches.txt >> .ci-prod-requirements.txt

# qa env
requirements-builder --level=pypi setup.py > .ci-qa-requirements.txt.tmp
remove_topical .ci-qa-requirements.txt.tmp > .ci-qa-requirements.txt
cat requirements.topical.branches.txt >> .ci-qa-requirements.txt

# devel env
requirements-builder --level=dev --req requirements.devel.txt setup.py > .ci-devel-requirements.txt.tmp
remove_devel .ci-devel-requirements.txt.tmp > .ci-devel-requirements.txt
