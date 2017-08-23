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
remove_topical requirements.pinned.txt > .travis-production-requirements.txt
cat requirements.topical.branches.txt >> .travis-production-requirements.txt

# release env
requirements-builder --level=pypi setup.py > .travis-release-requirements.txt.tmp
remove_topical .travis-release-requirements.txt.tmp > .travis-release-requirements.txt
cat requirements.topical.branches.txt >> .travis-release-requirements.txt

# devel env
requirements-builder --level=dev --req requirements.devel.txt setup.py > .travis-devel-requirements.txt.tmp
remove_devel .travis-devel-requirements.txt.tmp > .travis-devel-requirements.txt
