/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

import React, { useState } from "react";
import PropTypes from "prop-types";
import { ReactSearchKit } from "react-searchkit";

import { SearchStateBridge } from "./hooks";
import { DEFAULT_PARAMS, paramsToQueryState } from "./params";
import { CDSSearchApi } from "./searchApi";
import { CDSUrlHandlerApi } from "./urlHandler";

let appCounter = 0;

/**
 * A react-searchkit app on a CDS REST endpoint (``<invenio-search>``).
 *
 * With ``disableUrlHandler``, the search is not reflected in the URL (home
 * page sections, related videos).
 */
export function SearchApp({
  endpoint,
  headers = {},
  extraParams = {},
  hiddenParams = {},
  disableUrlHandler = false,
  appName = null,
  children,
}) {
  const [config] = useState(() => {
    const searchApi = new CDSSearchApi({ endpoint, headers });
    const initialParams = { ...DEFAULT_PARAMS, ...extraParams };
    appCounter += 1;
    return {
      searchApi,
      appName: appName || `cds-search-${appCounter}`,
      initialQueryState: paramsToQueryState(initialParams, hiddenParams),
      urlHandlerApi: disableUrlHandler
        ? { enabled: false }
        : {
            enabled: true,
            customHandler: new CDSUrlHandlerApi({ extraParams, hiddenParams }),
          },
    };
  });
  return (
    <ReactSearchKit
      appName={config.appName}
      searchApi={config.searchApi}
      urlHandlerApi={config.urlHandlerApi}
      initialQueryState={config.initialQueryState}
      searchOnInit
    >
      <SearchStateBridge searchApi={config.searchApi}>
        {children}
      </SearchStateBridge>
    </ReactSearchKit>
  );
}

SearchApp.propTypes = {
  endpoint: PropTypes.string.isRequired,
  headers: PropTypes.object,
  extraParams: PropTypes.object,
  hiddenParams: PropTypes.object,
  disableUrlHandler: PropTypes.bool,
  appName: PropTypes.string,
  children: PropTypes.node.isRequired,
};
