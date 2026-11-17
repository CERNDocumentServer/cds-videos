/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Loading state, errors and count of a search. */

import React from "react";
import PropTypes from "prop-types";
import { Message, Segment } from "semantic-ui-react";

import { joinArray } from "@js/cds/shared/utils/text";
import { isoToLanguage } from "@js/cds/shared/utils/languages";

import { LinePlaceholder } from "./Placeholders";
import { useSearch } from "../hooks";

/** True until the first results (or error) of the search arrive. */
export function isFirstLoad(state) {
  return !state.results.hits && !state.error;
}

/** Loading message of a search. */
export function SearchLoading({ message = "", className = null }) {
  const [state] = useSearch();
  if (!state.loading) {
    return null;
  }
  return (
    <div className={["loading", className].filter(Boolean).join(" ")}>
      <i className="fa fa-spinner" /> {message}
    </div>
  );
}

SearchLoading.propTypes = {
  message: PropTypes.string,
  className: PropTypes.string,
};

/** Error message of a search. */
export function SearchError() {
  const [state] = useSearch();
  if (!(state.error && state.errorResults && state.errorResults.message)) {
    return null;
  }
  return (
    <Message negative className="cds-search-error">
      <i className="fa fa-bolt" />
      <strong>Error:</strong> {state.errorResults.message}
    </Message>
  );
}

/** Number of results of a search. */
export function SearchCount() {
  const [state] = useSearch();
  const total = state.results.hits ? state.results.hits.total : undefined;
  // The count of the previous search would describe the placeholders
  if (state.loading || isFirstLoad(state)) {
    return <LinePlaceholder className="cds-placeholder-count" />;
  }
  if (total === 0) {
    const params = state.currentParams || {};
    return (
      <div>
        <Segment secondary className="cds-well">
          <div className="text-center mb-20">
            <i className="fa fa-search f2" />
          </div>
          <p className="f5">no results found</p>
          {Object.keys(params)
            .filter((key) => ["page", "size"].indexOf(key) === -1)
            .map((key) => {
              const value = params[key];
              return (
                <div key={key}>
                  {key === "q" && value !== "" && (
                    <p className="f6">
                      for &quot;<em>{value}</em>&quot;
                    </p>
                  )}
                  {key !== "q" && (
                    <p>
                      <strong className="text-capitalize">{key + ":"}</strong>{" "}
                      <em>{isoToLanguage(joinArray(value))}</em>
                    </p>
                  )}
                </div>
              );
            })}
          <p />
        </Segment>
      </div>
    );
  }
  if (total > 0) {
    return (
      <div>{total === 1 ? "Found 1 result" : `Found ${total} results`}</div>
    );
  }
  return null;
}
