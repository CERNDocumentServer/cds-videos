/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Sort and page size menus of a search. */

import React from "react";
import PropTypes from "prop-types";
import { Dropdown } from "semantic-ui-react";

import { filterByText } from "@js/cds/shared/utils/collections";

import { useSearch } from "../hooks";

export function SearchSelectBox({ sortKey = "sort", availableOptions }) {
  const [state, store] = useSearch();
  const options = (availableOptions && availableOptions.options) || [];

  const strip = (value) =>
    value && value.charAt(0) === "-" ? value.slice(1, value.length) : value;
  let selectedOption =
    strip(state.args[sortKey]) ||
    strip(state.sortArgs[sortKey]) ||
    (state.args[sortKey] === undefined && options.length ? null : null);
  if (!selectedOption) {
    selectedOption = options.length ? options[0].value : null;
  }
  // The template shows the first option whose properties contain the value
  const match = filterByText(options, selectedOption)[0];
  const title = (match && match.title) || "Select";

  return (
    <Dropdown
      className="cds-select-btn text-capitalize"
      button
      basic
      icon={null}
      trigger={
        <span>
          Sort: {title} <span className="cds-caret" />
        </span>
      }
    >
      <Dropdown.Menu>
        {options.map((option) => (
          <Dropdown.Item
            key={option.value}
            text={option.title}
            onClick={() => store.setArgs({ [sortKey]: option.value })}
          />
        ))}
      </Dropdown.Menu>
    </Dropdown>
  );
}

SearchSelectBox.propTypes = {
  sortKey: PropTypes.string,
  availableOptions: PropTypes.object.isRequired,
};
