/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Text, text area, select, checkbox and date fields. */

import React from "react";
import PropTypes from "prop-types";
import clsx from "clsx";
import _toPath from "lodash/toPath";

import { DatePickerInput } from "./DatePicker";
import { useDepositField, useReadonly } from "./formContext";
import { FormGroup } from "./FormGroup";

/* Text input */
export function TextField({
  name,
  label = null,
  placeholder = "",
  description = null,
  required = false,
  readonly = false,
  notitle = false,
}) {
  const { value, error, setValue } = useDepositField(name);
  const disabled = useReadonly(readonly);
  return (
    <FormGroup
      label={label}
      required={required}
      error={error}
      description={description}
      notitle={notitle}
    >
      <input
        type="text"
        name={_toPath(name).slice(-1)[0]}
        className="cds-form-control"
        placeholder={placeholder}
        value={value ?? ""}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
      />
    </FormGroup>
  );
}

TextField.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.string,
  placeholder: PropTypes.string,
  description: PropTypes.node,
  required: PropTypes.bool,
  readonly: PropTypes.bool,
  notitle: PropTypes.bool,
};

/* Text area */
export function TextAreaField({
  name,
  label = null,
  placeholder = "",
  description = null,
  required = false,
}) {
  const { value, error, setValue } = useDepositField(name);
  const disabled = useReadonly();
  return (
    <FormGroup
      label={label}
      required={required}
      error={error}
      description={description}
      nbsp={false}
    >
      <textarea
        className="cds-form-control"
        name={_toPath(name).slice(-1)[0]}
        placeholder={placeholder}
        value={value || ""}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
      />
    </FormGroup>
  );
}

TextAreaField.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.string,
  placeholder: PropTypes.string,
  description: PropTypes.node,
  required: PropTypes.bool,
};

/* Select with fixed options */
export function SelectField({
  name,
  label = null,
  options,
  description = null,
  required = false,
  readonly = false,
  onChange = null,
}) {
  const { value, error, setValue } = useDepositField(name);
  const disabled = useReadonly(readonly);
  const known = options.some((option) => option.value === value);
  return (
    <FormGroup
      label={label}
      required={required}
      error={error}
      description={description}
      nbsp={false}
    >
      <select
        className="cds-form-control"
        name={_toPath(name).slice(-1)[0]}
        value={known ? value : ""}
        disabled={disabled}
        onChange={(e) => {
          const option = options.find(
            (item) => String(item.value) === e.target.value
          );
          const newValue = option ? option.value : undefined;
          setValue(newValue);
          if (onChange) onChange(newValue);
        }}
      >
        {!known && <option value="" />}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.name}
          </option>
        ))}
      </select>
    </FormGroup>
  );
}

SelectField.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.string,
  options: PropTypes.array.isRequired,
  description: PropTypes.node,
  required: PropTypes.bool,
  readonly: PropTypes.bool,
  onChange: PropTypes.func,
};

/* Checkbox */
export function CheckboxField({ name, label, description = null }) {
  const { value, error, setValue } = useDepositField(name);
  const disabled = useReadonly();
  return (
    <div className={clsx("cds-checkbox", error && "has-error")}>
      <label>
        <input
          type="checkbox"
          name={_toPath(name).slice(-1)[0]}
          checked={Boolean(value)}
          disabled={disabled}
          onChange={(e) => setValue(e.target.checked)}
        />{" "}
        <span>{label}</span>
      </label>
      <div className="help-block">{error || description}</div>
    </div>
  );
}

CheckboxField.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  description: PropTypes.node,
};

/* Date */
export function DateField({
  name,
  label = null,
  placeholder = "",
  description = null,
  required = false,
}) {
  const { value, error, setValue } = useDepositField(name);
  const disabled = useReadonly();
  return (
    <FormGroup
      label={label}
      required={required}
      error={error}
      faIcon="fa-calendar"
      className="schema-form-datepicker"
      noHelp
    >
      <div>
        <DatePickerInput
          name={_toPath(name).slice(-1)[0]}
          placeholder={placeholder}
          value={value || ""}
          disabled={disabled}
          onChange={setValue}
        />
        <span className="help-block">{error || description}</span>
      </div>
    </FormGroup>
  );
}

DateField.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.string,
  placeholder: PropTypes.string,
  description: PropTypes.node,
  required: PropTypes.bool,
};
