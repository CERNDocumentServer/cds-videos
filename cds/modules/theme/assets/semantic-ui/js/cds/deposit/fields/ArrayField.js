/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/**
 * A list of items, each with its own fields, that can be added, removed and
 * sorted.
 */

import React, { useEffect } from "react";
import PropTypes from "prop-types";
import clsx from "clsx";

import { prevent } from "@js/cds/shared/dom";

import { setRecordValue } from "../state/deposit";
import { useDepositField, useReadonly } from "./formContext";

export function ArrayField({
  name,
  label = null,
  required = false,
  add = null,
  description = null,
  inline = false,
  firstItemMessage = null,
  notitle = false,
  startEmpty = true,
  newItem = null,
  renderItem,
}) {
  const { value, error, setValue, formik, id, dispatch } =
    useDepositField(name);
  const disabled = useReadonly();
  const items = Array.isArray(value) ? value : [];

  // ``startEmpty: false``: an empty array gets a first item
  useEffect(() => {
    if (!startEmpty && items.length === 0) {
      const next = [{}];
      formik.setFieldValue(name, next, false);
      dispatch(setRecordValue(id, name, next));
    }
    // Only when the form is created
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      className={clsx(
        "form-group schema-form-array clearfix",
        error && "has-error"
      )}
    >
      {!notitle && label && (
        <label className={clsx("control-label", required && "field-required")}>
          {" "}
          {label}
        </label>
      )}
      <ul className="list-unstyled">
        {items.map((item, index) => {
          const first = Boolean(firstItemMessage) && index === 0;
          return (
            // eslint-disable-next-line react/no-array-index-key
            <li
              key={index}
              className={clsx(
                "cds-list-group-item",
                inline && "deposit-inline",
                first && "bg-warn"
              )}
            >
              {!first && (
                <div
                  className={clsx(
                    "close-container pull-right",
                    !inline && "clear-form"
                  )}
                  style={{ paddingBottom: "20px" }}
                >
                  {!(disabled || items.length <= 1) && (
                    <button
                      className="cds-close"
                      type="button"
                      onClick={() => {
                        const next = items.filter((_item, i) => i !== index);
                        setValue(next);
                      }}
                    >
                      <span aria-hidden="true">&times;</span>
                    </button>
                  )}
                </div>
              )}
              {first && (
                <div className="pb-20">
                  <span className="ui label cds-label cds-label-default">
                    {firstItemMessage}
                  </span>
                </div>
              )}
              <div className="cds-clearfix" />
              {renderItem(`${name}.${index}`, index)}
            </li>
          );
        })}
      </ul>
      <div>
        {(error || description) && (
          <div className="help-block">{error || description}</div>
        )}
        {!disabled && (
          <a
            href="#add"
            className="add-button"
            onClick={prevent(() =>
              setValue(items.concat([newItem ? newItem() : {}]))
            )}
          >
            <i className="fa fa-plus" />
            &nbsp;{add || "Add"}
          </a>
        )}
      </div>
    </div>
  );
}

ArrayField.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.string,
  required: PropTypes.bool,
  add: PropTypes.string,
  description: PropTypes.node,
  inline: PropTypes.bool,
  firstItemMessage: PropTypes.string,
  notitle: PropTypes.bool,
  startEmpty: PropTypes.bool,
  newItem: PropTypes.func,
  renderItem: PropTypes.func.isRequired,
};
