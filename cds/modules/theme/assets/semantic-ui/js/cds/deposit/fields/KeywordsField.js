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
import { useStore } from "react-redux";

import { AsyncMultiSelect } from "./AsyncSelect";
import { autocompleteKeywords, formatTokenTags } from "./autocomplete";
import { useDepositField, useReadonly } from "./formContext";
import { FormGroup } from "./FormGroup";

/* Keywords: a multiple select with suggestions, new keywords allowed */
export function KeywordsField({
  name,
  label = null,
  placeholder = "",
  description = null,
}) {
  const { value, error, setValue, id } = useDepositField(name);
  const disabled = useReadonly();
  const store = useStore();
  // The keywords of the record when the form is created, as before
  const [fetch] = useState(() => {
    const { keywords } = store.getState().deposits[id].record;
    return (query) => autocompleteKeywords(keywords)(query);
  });
  return (
    <FormGroup
      label={label}
      error={error}
      description={description}
      nbsp={false}
    >
      <AsyncMultiSelect
        values={value || []}
        getName={(item) => item.name}
        toItem={formatTokenTags}
        fetchOptions={fetch}
        minLength={1}
        delay={100}
        disabled={disabled}
        placeholder={placeholder}
        allowAdditions
        onChange={setValue}
      />
    </FormGroup>
  );
}

KeywordsField.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.string,
  placeholder: PropTypes.string,
  description: PropTypes.node,
};
