/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

import {
  DEFAULT_PARAMS,
  paramsToQueryState,
  parseLocationSearch,
  queryStateToParams,
  toLocationSearch,
} from "./params";

/**
 * react-searchkit URL handler keeping the URLs of the former interface
 * (``?page=1&size=21&q=atlas&collections=ATLAS&years=2010--2020``).
 *
 * - when the page is opened, the parameters are the defaults, merged with
 *   the extra parameters and then with the URL ones, and the URL is replaced
 *   with all of them;
 * - every new search adds an entry to the browser history, unless the URL
 *   does not change;
 * - the parameters keep their order in the URL, new ones are appended.
 */
export class CDSUrlHandlerApi {
  constructor({ extraParams = {}, hiddenParams = {} } = {}) {
    this.extraParams = extraParams || {};
    this.hiddenParams = hiddenParams || {};
    this.keyOrder = [];
    this.get = this.get.bind(this);
    this.set = this.set.bind(this);
    this.replace = this.replace.bind(this);
  }

  /** Parameters of the current URL merged with the defaults. */
  urlParams() {
    return {
      ...DEFAULT_PARAMS,
      ...this.extraParams,
      ...parseLocationSearch(window.location.search),
    };
  }

  /** Query state from the URL (called on init and on popstate). */
  get(initialQueryState = {}) {
    const params = this.urlParams();
    this.keyOrder = Object.keys(params);
    const queryState = {
      ...initialQueryState,
      ...paramsToQueryState(params, this.hiddenParams),
    };
    this.replace(queryState);
    return queryState;
  }

  url(queryState) {
    const params = queryStateToParams(queryState, this.keyOrder);
    this.keyOrder = Object.keys(params);
    return (
      window.location.pathname + toLocationSearch(params) + window.location.hash
    );
  }

  isCurrent(url) {
    return (
      url ===
      window.location.pathname + window.location.search + window.location.hash
    );
  }

  set(queryState) {
    const url = this.url(queryState);
    if (!this.isCurrent(url) && window.history.pushState) {
      window.history.pushState({ path: url }, "", url);
    }
  }

  replace(queryState) {
    const url = this.url(queryState);
    if (!this.isCurrent(url) && window.history.replaceState) {
      window.history.replaceState({ path: url }, "", url);
    }
  }
}
