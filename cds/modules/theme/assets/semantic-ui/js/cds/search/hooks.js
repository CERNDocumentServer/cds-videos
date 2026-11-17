/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/*
 * Bridge between the react-searchkit state and the CDS search components.
 *
 * The components read the search state: the current
 * parameters (``{page, size, q, sort, <facet>: [...]}``), the REST API
 * response and its loading and error states. They change the search through
 * ``changeParams`` and ``setArgs``, which update the react-searchkit query
 * state (and so the request, the URL and the browser history).
 */

import React, { useContext, useRef } from "react";
import PropTypes from "prop-types";
import _isEmpty from "lodash/isEmpty";
import _isEqual from "lodash/isEqual";
import { withState } from "react-searchkit";

import {
  changedParams,
  paramsToQueryState,
  parseURLQueryString,
  queryStateToParams,
} from "./params";

export const SearchContext = React.createContext(null);

/** ``sortArgs``: arguments of the response ``links.self`` (server defaults). */
function sortArgsOf(links, currentParams) {
  if (!links || !links.self) {
    return null;
  }
  const data = parseURLQueryString(links.self);
  if (data.page) data.page = parseInt(data.page, 10);
  if (data.size) data.size = parseInt(data.size, 10);
  delete data.q;
  return _isEqual(currentParams, data) ? null : data;
}

function SearchStateBridgeComponent({
  currentQueryState,
  currentResultsState,
  updateQueryState,
  searchApi,
  children = null,
}) {
  const memory = useRef({ results: {}, sortArgs: {}, responses: 0 });
  const params = queryStateToParams(currentQueryState);
  const error = _isEmpty(currentResultsState.error)
    ? null
    : currentResultsState.error;

  // Keep the last results on errors, like invenio-search-js did
  if (!currentResultsState.loading && !error && searchApi.responses > 0) {
    if (memory.current.responses !== searchApi.responses) {
      memory.current.responses = searchApi.responses;
      const data = currentResultsState.data;
      memory.current.results = {
        hits: { hits: data.hits, total: data.total },
        aggregations: data.aggregations,
        links: searchApi.links,
      };
      const sortArgs = sortArgsOf(searchApi.links, params);
      if (sortArgs) {
        memory.current.sortArgs = sortArgs;
      }
    }
  }

  const state = {
    results: memory.current.results,
    loading: currentResultsState.loading,
    error,
    errorResults: (error && error.response && error.response.data) || {},
    currentParams: params,
    args: params,
    sortArgs: memory.current.sortArgs,
  };

  const request = (changes) => {
    const next = changedParams(params, changes);
    if (next) {
      updateQueryState({
        ...paramsToQueryState(next),
        hiddenParams: currentQueryState.hiddenParams,
      });
    }
  };

  const store = {
    changeParams: request,
    setArgs: request,
    queryState: currentQueryState,
  };

  return (
    <SearchContext.Provider value={{ state, store }}>
      {children}
    </SearchContext.Provider>
  );
}

SearchStateBridgeComponent.propTypes = {
  currentQueryState: PropTypes.object.isRequired,
  currentResultsState: PropTypes.object.isRequired,
  updateQueryState: PropTypes.func.isRequired,
  searchApi: PropTypes.object.isRequired,
  children: PropTypes.node,
};

export const SearchStateBridge = withState(SearchStateBridgeComponent);

/** Return ``[state, store]`` of the closest search. */
export function useSearch() {
  const { state, store } = useContext(SearchContext);
  return [state, store];
}

/** Subscribe to a store with ``state`` and ``subscribe`` (search bar). */
export function useStoreState(store) {
  const [state, setState] = React.useState(store.state);
  React.useEffect(() => {
    setState(store.state);
    return store.subscribe(setState);
  }, [store]);
  return state;
}
