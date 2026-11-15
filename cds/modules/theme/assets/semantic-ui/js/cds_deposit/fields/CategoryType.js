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
 * Category and type of the project (``strapselect`` with the categories of
 * ``/api/categories``).
 */

import React from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import { Dropdown } from "semantic-ui-react";

import { setRecordValue } from "../state/deposit";
import { changeCategoryOrType } from "../state/permissions";
import { selectAnyVideoPublished } from "../state/selectors";
import { useDepositField, useDepositForm, useReadonly } from "./Fields";

const DESCRIPTIONS = {
  category: "Category of the project.",
  type: "Type of the project.",
};

/** Types of all the categories, keeping a legacy type of the record. */
export function typesOf(categories, recordType) {
  return [].concat(
    ...categories.map((category) => {
      const types = [...category.metadata.types];
      if (recordType && types.indexOf(recordType) === -1) {
        types.push(recordType);
      }
      return types.map((type) => ({
        name: type,
        value: type,
        category: category.metadata.name,
      }));
    })
  );
}

function StrapSelect({
  name,
  label,
  options,
  readonly = false,
  description = null,
  onChange = null,
}) {
  const { value, error, setValue } = useDepositField(name);
  const disabled = useReadonly(readonly);
  return (
    <fieldset
      className={[
        "field form-group cds-deposit-strap-select",
        error && "has-error",
      ]
        .filter(Boolean)
        .join(" ")}
      disabled={disabled}
    >
      <label className="field-required">
        {" "}
        {label}
      </label>
      <div className="form-group">
        <Dropdown
          fluid
          selection
          icon={<span className="cds-caret" />}
          disabled={disabled}
          placeholder={label}
          options={options.map((option) => ({
            key: option.value,
            value: option.value,
            text: option.name,
          }))}
          value={value || null}
          selectOnBlur={false}
          onChange={(e, data) => {
            setValue(data.value);
            if (onChange) onChange(data.value);
          }}
        />
        <span className="help-block">{error || description}</span>
      </div>
    </fieldset>
  );
}

StrapSelect.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  options: PropTypes.array.isRequired,
  readonly: PropTypes.bool,
  description: PropTypes.node,
  onChange: PropTypes.func,
};

export function CategoryField({ withDescription = false }) {
  const { id } = useDepositForm();
  const dispatch = useDispatch();
  const { formik } = useDepositField("type");
  const categories = useSelector((state) => state.page.categories);
  const anyVideoPublished = useSelector(selectAnyVideoPublished);
  return (
    <StrapSelect
      name="category"
      label="Category"
      readonly={anyVideoPublished}
      description={withDescription ? DESCRIPTIONS.category : null}
      options={categories.map((category) => ({
        name: category.metadata.name,
        value: category.metadata.name,
      }))}
      onChange={() => {
        // Invalidate any previously selected type
        formik.setFieldValue("type", undefined);
        dispatch(setRecordValue(id, "type", undefined));
        dispatch(changeCategoryOrType());
      }}
    />
  );
}

CategoryField.propTypes = { withDescription: PropTypes.bool };

export function TypeField({ withDescription = false }) {
  const { id } = useDepositForm();
  const dispatch = useDispatch();
  const { formik } = useDepositField("type");
  const categories = useSelector((state) => state.page.categories);
  const anyVideoPublished = useSelector(selectAnyVideoPublished);
  const record = useSelector((state) => state.deposits[id].record);
  const category = formik.values.category;
  const options = typesOf(categories, record.type).filter(
    (item) => item.category === category
  );
  return (
    <StrapSelect
      name="type"
      label="Type"
      readonly={!record.category || anyVideoPublished}
      description={withDescription ? DESCRIPTIONS.type : null}
      options={options}
      onChange={() => dispatch(changeCategoryOrType())}
    />
  );
}

TypeField.propTypes = { withDescription: PropTypes.bool };
