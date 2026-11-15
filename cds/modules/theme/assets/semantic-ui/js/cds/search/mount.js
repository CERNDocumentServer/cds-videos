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
 * Mount a search page: one react-searchkit app for the element carrying the
 * ``data-search-*`` attributes (like ``<invenio-search>``), rendering one
 * portal per ``[data-cds-search-component]`` placeholder inside it. The
 * placeholders are spread in the page rendered by Jinja (header, facets
 * column, results column) and share the same search state.
 */

import PropTypes from "prop-types";
import React, { useEffect, useRef, useState } from "react";
import ReactDOM from "react-dom";
import { createRoot } from "react-dom/client";

import { LoadingBar } from "../components/LoadingBar";
import { VIDEO_PLACEHOLDERS } from "../components/Placeholders";
import { SearchBarSuggestions } from "../components/SearchBarSuggestions";
import { VIDEO_TEMPLATES } from "../components/VideoTemplates";
import { parseJSON } from "../dom";
import {
  DepositSearchFacets,
  SearchCount,
  SearchError,
  SearchFacets,
  SearchLoading,
  SearchPagination,
  SearchRange,
  SearchResults,
  SearchSelectBox,
} from "./components";
import { useSearch } from "./hooks";
import { SearchApp } from "./SearchApp";

/** Mount the loading bar once per page (``angular-loading-bar``). */
export function mountLoadingBar() {
  if (document.getElementById("cds-loading-bar-root")) {
    return;
  }
  const element = document.createElement("div");
  element.id = "cds-loading-bar-root";
  document.body.appendChild(element);
  createRoot(element).render(<LoadingBar />);
}

/**
 * Search bar of the header wired to the search (``invenio-search-bar``):
 * the input follows the query of the search, the search runs on enter or
 * on click.
 */
function HeaderSearchBar({ data }) {
  const [state, store] = useSearch();
  const query = state.currentParams.q || "";
  const listeners = useRef(new Set());
  const [adapter] = useState(() => ({
    state: { userQuery: query },
    subscribe(listener) {
      listeners.current.add(listener);
      return () => listeners.current.delete(listener);
    },
    setUserQuery(userQuery) {
      // A plain store object, not a component
      // eslint-disable-next-line react/no-direct-mutation-state
      this.state = { ...this.state, userQuery };
      listeners.current.forEach((listener) => listener(this.state));
    },
    setArgs: null,
  }));
  adapter.setArgs = (changes) => store.setArgs(changes);

  useEffect(() => {
    if (adapter.state.userQuery !== query) {
      adapter.setUserQuery(query);
    }
  }, [adapter, query]);

  return (
    <SearchBarSuggestions
      store={adapter}
      placeholder={data.placeholder}
      formId={data.formId || "cdsSearchFormSuggest"}
    />
  );
}

HeaderSearchBar.propTypes = {
  data: PropTypes.shape({
    placeholder: PropTypes.string,
    formId: PropTypes.string,
  }).isRequired,
};

/**
 * Components available to the placeholders, keyed by the value of
 * ``data-cds-search-component``. Each one gets the ``dataset`` of its
 * placeholder, the result templates and their loading placeholders.
 */
export const SEARCH_COMPONENTS = {
  searchbar: HeaderSearchBar,
  range: ({ data }) => <SearchRange options={parseJSON(data.options, {})} />,
  facets: ({ data }) =>
    data.variant === "deposit" ? <DepositSearchFacets /> : <SearchFacets />,
  count: () => <SearchCount />,
  sort: ({ data }) => (
    <SearchSelectBox
      sortKey={data.sortKey || "sort"}
      availableOptions={parseJSON(data.options, { options: [] })}
    />
  ),
  error: () => <SearchError />,
  loading: ({ data }) => <SearchLoading message={data.message || ""} />,
  results: ({ data, templates, placeholders }) => (
    <SearchResults
      template={templates[data.template]}
      placeholder={placeholders[data.template]}
    />
  ),
  pagination: ({ data }) => (
    <SearchPagination
      variant={data.variant || "cds"}
      adjacentSize={data.adjacentSize ? parseInt(data.adjacentSize, 10) : 4}
    />
  ),
};

/**
 * Create the search app of ``root`` and render its components into the
 * placeholders.
 *
 * ``options.components`` and ``options.templates`` extend the default
 * components and result templates. ``options.placeholders`` extend the
 * Semantic UI placeholders shown instead of a result template while the
 * search is loading (keyed like the templates).
 */
export function mountSearchApp(root, options = {}) {
  const data = root.dataset;
  const components = { ...SEARCH_COMPONENTS, ...(options.components || {}) };
  const templates = { ...VIDEO_TEMPLATES, ...(options.templates || {}) };
  const placeholders = {
    ...VIDEO_PLACEHOLDERS,
    ...(options.placeholders || {}),
  };

  const elements = Array.from(
    root.querySelectorAll("[data-cds-search-component]")
  );
  // The server rendered content is replaced by the components
  elements.forEach((element) => {
    element.innerHTML = "";
  });
  const portals = elements
    .map((element, index) => {
      const Component = components[element.dataset.cdsSearchComponent];
      if (!Component) return null;
      return ReactDOM.createPortal(
        <Component
          data={element.dataset}
          templates={templates}
          placeholders={placeholders}
        />,
        element,
        `cds-search-portal-${index}`
      );
    })
    .filter(Boolean);

  const container = document.createElement("div");
  container.className = "cds-search-app";
  root.appendChild(container);
  createRoot(container).render(
    <SearchApp
      endpoint={data.searchEndpoint}
      headers={parseJSON(data.searchHeaders, {})}
      extraParams={parseJSON(data.searchExtraParams, {})}
      hiddenParams={parseJSON(data.searchHiddenParams, {})}
      disableUrlHandler={data.searchDisableUrlHandler === "true"}
      appName={data.searchAppName || null}
    >
      {portals}
    </SearchApp>
  );

  if (options.loadingBar !== false) {
    mountLoadingBar();
  }
}
