/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

import React, { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import DOMPurify from "dompurify";
import _find from "lodash/find";
import _isEmpty from "lodash/isEmpty";

import { http, storage } from "@js/cds/shared/api";
import { useStoreState } from "@js/cds/search/hooks";

/* Same storage key as the previous interface (prefix ``ls``). */
const HISTORY_PREFIX = "ls";
const HISTORY_KEY = "cds.search.history";
const HISTORY_ICON = '<i class="fa fa-history text-primary pr-5"></i> ';

const DEBOUNCE = { attach: 300, suggest: 200, blur: 150 };

/** Remote suggestions: title completion, then search history. */
export async function suggestStateRemote(term) {
  const response = await http.get("/api/records/_suggest", {
    params: { "suggest-title": term, size: 10 },
    ignoreLoadingBar: true,
  });
  const options =
    (response.data["suggest-title"] &&
      response.data["suggest-title"][0] &&
      response.data["suggest-title"][0].options) ||
    [];
  const titles = options
    .map((opt) => {
      const title =
        (opt._source && opt._source.title && opt._source.title.title) ||
        opt.text;
      return title ? { label: title, value: title } : null;
    })
    .filter(Boolean);
  return titles.concat(storage.get(HISTORY_PREFIX, HISTORY_KEY) || []);
}

/** Store a search in the history (``searchSuggestions.onSelect``). */
export function addToHistory(selected) {
  if (selected && !_isEmpty(selected.value)) {
    try {
      const searches = storage.get(HISTORY_PREFIX, HISTORY_KEY) || [];
      const exists = _find(searches, { value: selected.value });
      if (exists === undefined) {
        if (searches.length > 4) {
          searches.pop();
        }
        searches.push({
          label: HISTORY_ICON + selected.label,
          value: selected.value,
        });
        storage.set(HISTORY_PREFIX, HISTORY_KEY, searches);
      }
      return true;
    } catch (error) {
      return false;
    }
  }
  return false;
}

function SuggestionLabel({ label = "" }) {
  // The label is HTML (the history entries carry their icon)
  return (
    <span
      dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(label || "") }}
    />
  );
}

SuggestionLabel.propTypes = { label: PropTypes.string };

/**
 * Header search bar with suggestions. On the search page it is wired to
 * the search when a search ``store`` is given.
 */
export function SearchBarSuggestions({
  action = "/search",
  placeholder = "Search CDS",
  store = null,
  formId = "cdsSearchFormSuggest",
}) {
  const searchState = useStoreState(store || NULL_STORE);
  const inSearch = Boolean(store);
  const [value, setValue] = useState(
    inSearch ? searchState.userQuery || "" : ""
  );
  const [focused, setFocused] = useState(false);
  const [results, setResults] = useState([]);
  const [show, setShow] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef(null);
  const formRef = useRef(null);
  const timers = useRef({});
  const waiting = useRef(false);
  const lastSelected = useRef(undefined);
  const previousValue = useRef(undefined);
  const attached = useRef(false);

  // Keep the input in sync with the query of the search (search page)
  useEffect(() => {
    if (inSearch) {
      setValue(searchState.userQuery || "");
    }
  }, [inSearch, searchState.userQuery]);

  useEffect(() => {
    const current = timers.current;
    return () => Object.values(current).forEach((t) => clearTimeout(t));
  }, []);

  function hide() {
    setShow(false);
    setSelectedIndex(-1);
  }

  function suggest(term) {
    clearTimeout(timers.current.suggest);
    timers.current.suggest = setTimeout(async () => {
      setSelectedIndex(0);
      waiting.current = true;
      if (typeof term === "string" && term.length > 0) {
        try {
          const suggestions = await suggestStateRemote(term);
          if (!attached.current) return;
          if (suggestions && suggestions.length > 0) {
            setResults([{ value: term, label: "" }].concat(suggestions));
            setShow(true);
          } else {
            setResults([]);
            hide();
          }
        } catch {
          hide();
        } finally {
          waiting.current = false;
        }
      } else {
        waiting.current = false;
        hide();
      }
    }, DEBOUNCE.suggest);
  }

  function onFocus() {
    if (inSearch) setFocused(true);
    clearTimeout(timers.current.attach);
    timers.current.attach = setTimeout(() => {
      if (document.activeElement !== inputRef.current) return;
      if (!inSearch) setFocused(true);
      attached.current = true;
      previousValue.current = inputRef.current.value;
      setResults([]);
      setSelectedIndex(-1);
    }, DEBOUNCE.attach);
  }

  function onBlur() {
    if (inSearch) setFocused(false);
    clearTimeout(timers.current.blur);
    timers.current.blur = setTimeout(() => {
      if (document.activeElement !== inputRef.current) {
        attached.current = false;
        if (!inSearch) setFocused(false);
        hide();
      }
    }, DEBOUNCE.blur);
  }

  function onChange(event) {
    const newValue = event.target.value;
    setValue(newValue);
    if (inSearch) {
      // Debounced by 500 ms on the search page
      clearTimeout(timers.current.model);
      timers.current.model = setTimeout(
        () => store.setUserQuery(newValue),
        500
      );
    }
    if (attached.current && newValue !== lastSelected.current) {
      suggest(newValue);
    }
  }

  function setSelection(index) {
    const selected = results[index];
    if (!selected) return undefined;
    // Show the value of the highlighted suggestion in the input
    setValue(selected.value);
    setSelectedIndex(index);
    return selected;
  }

  function updateQuery() {
    const query = value;
    if (inSearch) {
      clearTimeout(timers.current.model);
      store.setUserQuery(query);
      store.setArgs({ q: query });
    }
  }

  function onSelect(selected) {
    if (addToHistory(selected) && !inSearch) {
      // Submit the form to trigger the search
      setTimeout(() => formRef.current && formRef.current.submit());
    }
  }

  function applySelection(index) {
    inputRef.current.focus();
    if (!show || index > results.length || index < 0) return;
    const selected = setSelection(index);
    if (!selected) return;
    lastSelected.current = selected.value;
    setValue(selected.value);
    if (inSearch) {
      clearTimeout(timers.current.model);
      timers.current.model = setTimeout(
        () => store.setUserQuery(selected.value),
        500
      );
    }
    hide();
    onSelect(selected);
  }

  function onKeyDown(event) {
    if (event.shiftKey || !attached.current) return;
    switch (event.keyCode) {
      case 27: // ESC
        if (show) {
          hide();
        } else if (previousValue.current !== undefined) {
          setValue(previousValue.current);
        }
        break;
      case 13: // ENTER
        if (show && selectedIndex > 0 && !waiting.current) {
          applySelection(selectedIndex);
          event.stopPropagation();
          event.preventDefault();
          event.nativeEvent.__cdsSelection = true;
        }
        hide();
        break;
      case 9: // TAB
        if (!show) break;
        event.preventDefault();
      // falls through
      case 40: // DOWN
        if (results.length > 0) {
          if (show) {
            setSelection(
              selectedIndex + 1 > results.length - 1 ? 0 : selectedIndex + 1
            );
          } else {
            setShow(true);
            setSelection(0);
          }
        }
        break;
      case 38: // UP
        if (show) {
          event.preventDefault();
          setSelection(
            selectedIndex - 1 >= 0 ? selectedIndex - 1 : results.length - 1
          );
        }
        break;
      default:
        break;
    }
  }

  function onKeyUp(event) {
    if (inSearch && event.keyCode === 13 && !event.nativeEvent.__cdsSelection) {
      updateQuery();
    }
  }

  function onSubmit(event) {
    if (inSearch) {
      // No action on the search page form: the search is done in place
      event.preventDefault();
      return;
    }
    addToHistory({ label: value, value });
  }

  const active =
    focused || Boolean(inSearch ? searchState.userQuery || value : value);

  return (
    <form
      id={formId}
      ref={formRef}
      className={`cds-navbar-form${active ? " cds-active-search" : ""}`}
      action={inSearch ? undefined : action}
      role="search"
      onSubmit={onSubmit}
    >
      <div className="cds-navbar-form-group">
        <input
          ref={inputRef}
          autoComplete="off"
          id="cds-navbar-form-input"
          type="text"
          name="q"
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          onFocus={onFocus}
          onBlur={onBlur}
          onKeyDown={onKeyDown}
          onKeyUp={onKeyUp}
        />
        <div
          className="ac-container"
          role="listbox"
          style={{ display: show ? "block" : "none" }}
        >
          <ul className="ac-menu">
            {results.map((result, index) =>
              index > 0 ? (
                <li
                  key={`${index}-${result.value}`}
                  className={`ac-menu-item${
                    index === selectedIndex ? " ac-state-focus" : ""
                  }`}
                  role="option"
                  aria-selected={index === selectedIndex}
                >
                  <a
                    href="#suggestion"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={(e) => {
                      e.preventDefault();
                      applySelection(index);
                    }}
                  >
                    <SuggestionLabel label={result.label} />
                  </a>
                </li>
              ) : null
            )}
          </ul>
        </div>
      </div>
      <button
        type={inSearch ? "button" : "submit"}
        className="cds-hidden-xs cds-navbar-form-icon"
        aria-label="Search"
        onClick={inSearch ? updateQuery : undefined}
      >
        <i className="t-w fa fa-search" />
      </button>
      <button
        type={inSearch ? "button" : "submit"}
        className="cds-visible-xs ui basic button cds-navbar-form-icon-xs"
        onClick={inSearch ? updateQuery : undefined}
      >
        {inSearch ? (
          <>
            <i className="fa fa-search" />
            Search
          </>
        ) : (
          <i className="fa fa-search">Search</i>
        )}
      </button>
    </form>
  );
}

SearchBarSuggestions.propTypes = {
  action: PropTypes.string,
  placeholder: PropTypes.string,
  store: PropTypes.object,
  formId: PropTypes.string,
};

/* A store that never changes, used when there is no search store. */
const NULL_STORE = {
  state: {},
  subscribe: () => () => {},
};
