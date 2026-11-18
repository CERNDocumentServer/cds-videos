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
 * Selects with remote suggestions for the deposit forms, built on the
 * Semantic UI dropdown.
 */

import React, { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import { Dropdown } from "semantic-ui-react";

function useDebouncedSearch(fetchOptions, delay, minLength) {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const timer = useRef(null);
  const request = useRef(0);

  useEffect(() => () => clearTimeout(timer.current), []);

  const search = (query) => {
    clearTimeout(timer.current);
    if ((query || "").length < minLength) {
      request.current += 1;
      setResults([]);
      setLoading(false);
      return;
    }
    // Searching from the first key press, not only once the delay is over
    const current = ++request.current;
    setLoading(true);
    timer.current = setTimeout(async () => {
      let items = [];
      try {
        items = (await fetchOptions(query)) || [];
      } catch {
        // No suggestions
      }
      // Only the answer of the latest search
      if (current === request.current) {
        setResults(items);
        setLoading(false);
      }
    }, delay);
  };
  return [results, loading, search, setResults];
}

/** Highlight the search in a suggestion (``highlight`` filter of ui-select). */
function highlight(text, query) {
  const value = String(text || "");
  if (!query) return value;
  const index = value.toLowerCase().indexOf(query.toLowerCase());
  if (index === -1) return value;
  return (
    <>
      {value.slice(0, index)}
      <span className="ui-select-highlight">
        {value.slice(index, index + query.length)}
      </span>
      {value.slice(index + query.length)}
    </>
  );
}

/** The message of the menu when it has no suggestions. */
function searchStatus(query, minLength, loading) {
  if (!query) return null;
  if (query.length < minLength) return `Type at least ${minLength} characters`;
  return loading ? "Searching..." : "No results found.";
}

/**
 * Single value select with remote suggestions. ``fetchOptions(query)``
 * resolves to items ``{name, value, email}``, ``onSelect`` gets the item.
 * While it searches, a spinner replaces the caret and the menu says so.
 */
export function AsyncSelect({
  text = "",
  placeholder = "",
  fetchOptions,
  minLength = 2,
  delay = 100,
  disabled = false,
  onSelect,
  name = undefined,
}) {
  const [query, setQuery] = useState("");
  const [results, loading, search] = useDebouncedSearch(
    fetchOptions,
    delay,
    minLength
  );
  const options = [
    { key: "__current", value: "__current", text: text || "" },
  ].concat(
    results.map((item, index) => ({
      key: `r${index}`,
      value: `r${index}`,
      text: item.name,
      content: (
        <>
          <div>{highlight(item.name, query)}</div>
          {item.email && <small>&lt;{item.email}&gt;</small>}
        </>
      ),
    }))
  );
  return (
    <Dropdown
      fluid
      selection
      icon={
        // Semantic UI only animates an i.icon of a loading dropdown, not
        // the caret
        loading ? (
          <i
            className="cds-async-select-spinner notched circle loading icon"
            aria-label="Searching"
          />
        ) : (
          <span className="cds-caret" />
        )
      }
      name={name}
      disabled={disabled}
      placeholder={placeholder}
      options={options}
      value={text ? "__current" : null}
      text={text || undefined}
      searchQuery={query}
      selectOnBlur={false}
      selectOnNavigation={false}
      noResultsMessage={searchStatus(query, minLength, loading)}
      search={(opts) => opts.filter((option) => option.key !== "__current")}
      onSearchChange={(e, data) => {
        setQuery(data.searchQuery);
        search(data.searchQuery);
      }}
      onChange={(e, data) => {
        const match = /^r(\d+)$/.exec(data.value);
        if (match) {
          onSelect(results[parseInt(match[1], 10)]);
        }
        setQuery("");
      }}
      className="cds-async-select"
    />
  );
}

AsyncSelect.propTypes = {
  text: PropTypes.string,
  placeholder: PropTypes.string,
  fetchOptions: PropTypes.func.isRequired,
  minLength: PropTypes.number,
  delay: PropTypes.number,
  disabled: PropTypes.bool,
  onSelect: PropTypes.func.isRequired,
  name: PropTypes.string,
};

/**
 * Multiple values with remote suggestions and custom values (tagging with
 * ``,``). The values are objects; ``getName`` gives their label and
 * ``toItem`` builds a custom value.
 */
export function AsyncMultiSelect({
  values = [],
  getName,
  getText = null,
  toItem,
  fetchOptions,
  minLength = 1,
  delay = 100,
  disabled = false,
  placeholder = "",
  allowAdditions = false,
  onChange,
  noResultsMessage = () => null,
  renderResult = null,
  lockedValues = [],
}) {
  const [query, setQuery] = useState("");
  const [results, loading, search, setResults] = useDebouncedSearch(
    fetchOptions,
    delay,
    minLength
  );
  const current = values || [];
  const names = current.map(getName);

  const options = current
    .map((item, index) => ({
      // The values can repeat, as before
      key: `v-${index}-${getName(item)}`,
      value: getName(item),
      text: getText ? getText(item) : getName(item),
    }))
    .concat(
      results
        .filter((item) => names.indexOf(getName(item)) === -1)
        .map((item) => ({
          key: `r-${getName(item)}`,
          value: getName(item),
          text: getText ? getText(item) : getName(item),
          content: renderResult
            ? renderResult(item, query)
            : highlight(item.name, query),
        }))
    );

  const add = (name) => {
    const token = (name || "").trim();
    if (!token || names.indexOf(token) > -1) return;
    const found = results.find((item) => getName(item) === token);
    onChange(current.concat([found || toItem(token)]));
  };

  return (
    <Dropdown
      fluid
      multiple
      search
      selection
      disabled={disabled}
      loading={loading}
      placeholder={placeholder}
      options={options}
      value={names}
      searchQuery={query}
      allowAdditions={allowAdditions}
      additionLabel=""
      selectOnBlur={false}
      selectOnNavigation={false}
      noResultsMessage={noResultsMessage(query)}
      renderLabel={(item) => ({
        content: item.text,
        removeIcon: lockedValues.indexOf(item.value) > -1 ? null : undefined,
      })}
      onSearchChange={(e, data) => {
        const searchQuery = data.searchQuery;
        if (allowAdditions && searchQuery.indexOf(",") > -1) {
          searchQuery
            .split(",")
            .slice(0, -1)
            .forEach((token) => add(token));
          const rest = searchQuery.split(",").slice(-1)[0];
          setQuery(rest);
          search(rest);
          return;
        }
        setQuery(searchQuery);
        search(searchQuery);
      }}
      onChange={(e, data) => {
        const selected = data.value;
        const kept = current.filter(
          (item) =>
            selected.indexOf(getName(item)) > -1 ||
            lockedValues.indexOf(getName(item)) > -1
        );
        const added = selected
          .filter((name) => names.indexOf(name) === -1)
          .map(
            (name) =>
              results.find((item) => getName(item) === name) || toItem(name)
          );
        onChange(kept.concat(added));
        setQuery("");
        setResults([]);
      }}
      className="cds-async-select"
    />
  );
}

AsyncMultiSelect.propTypes = {
  values: PropTypes.array,
  getName: PropTypes.func.isRequired,
  getText: PropTypes.func,
  toItem: PropTypes.func.isRequired,
  fetchOptions: PropTypes.func.isRequired,
  minLength: PropTypes.number,
  delay: PropTypes.number,
  disabled: PropTypes.bool,
  placeholder: PropTypes.string,
  allowAdditions: PropTypes.bool,
  onChange: PropTypes.func.isRequired,
  noResultsMessage: PropTypes.func,
  renderResult: PropTypes.func,
  lockedValues: PropTypes.array,
};
