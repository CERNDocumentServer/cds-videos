/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Select field with options from an API (autocomplete). */

import React from "react";
import PropTypes from "prop-types";

import { AsyncSelect } from "./AsyncSelect";
import { parseAutocomplete } from "./autocomplete";
import { useDepositField, useReadonly } from "./formContext";
import { FormGroup } from "./FormGroup";

export function RemoteSelectField({
  name,
  errorName = null,
  label = null,
  placeholder = "",
  description = null,
  required = false,
  fetchOptions,
  minLength = 3,
  delay = 100,
  onSelect = null,
}) {
  const { value, error, setValue } = useDepositField(name, errorName);
  const disabled = useReadonly();
  return (
    <FormGroup
      label={label}
      required={required}
      error={error}
      description={description}
      className="schema-form-uiselect"
    >
      <AsyncSelect
        text={parseAutocomplete(value) || ""}
        // ui-select showed the placeholder only without a value (an empty
        // contributor ``{}`` is a value)
        placeholder={(value ?? "") === "" ? placeholder : ""}
        fetchOptions={fetchOptions}
        minLength={minLength}
        delay={delay}
        disabled={disabled}
        onSelect={(item) =>
          onSelect ? onSelect(item, setValue) : setValue(item.value)
        }
      />
    </FormGroup>
  );
}

RemoteSelectField.propTypes = {
  name: PropTypes.string.isRequired,
  errorName: PropTypes.string,
  label: PropTypes.string,
  placeholder: PropTypes.string,
  description: PropTypes.node,
  required: PropTypes.bool,
  fetchOptions: PropTypes.func.isRequired,
  minLength: PropTypes.number,
  delay: PropTypes.number,
  onSelect: PropTypes.func,
};
