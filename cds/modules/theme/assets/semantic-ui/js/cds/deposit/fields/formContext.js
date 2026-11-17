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
 * The form a field belongs to, and hooks to read and write its value. Every
 * change is also written to the deposit record (the actions send the
 * record) and marks the deposit dirty.
 */

import React, { useContext, useEffect } from "react";
import { getIn, useFormikContext } from "formik";
import _toPath from "lodash/toPath";
import { useDispatch, useSelector } from "react-redux";

import { setRecordValue } from "../state/deposit";
import { isPublished } from "../state/records";
import { registerField } from "../state/registry";

/** The deposit of the form: ``{id, type}``. */
export const DepositFormContext = React.createContext({ id: null, type: null });

export function useDepositForm() {
  return useContext(DepositFormContext);
}

/** Value, error and setter of a field. */
export function useDepositField(name, errorName) {
  const formik = useFormikContext();
  const dispatch = useDispatch();
  const { id } = useDepositForm();
  const errorPath = errorName || name;
  const value = getIn(formik.values, name);
  const touched = Boolean(getIn(formik.touched, name));
  const clientError = getIn(formik.errors, errorPath);
  const key = _toPath(name).join(".");
  // The server errors are shown on the field of the same key, as before
  const backendError = useSelector(
    (state) => state.deposits[id].backendErrors[key]
  );
  useEffect(() => registerField(id, key), [id, key]);
  const error =
    backendError ||
    (touched && typeof clientError === "string" ? clientError : null);
  const setValue = (newValue) => {
    formik.setFieldValue(name, newValue);
    formik.setFieldTouched(name, true, false);
    dispatch(setRecordValue(id, name, newValue));
  };
  return { value, error, setValue, formik, id, dispatch };
}

/** Read only when the deposit is published (``formDefaults.readonly``). */
export function useReadonly(extra) {
  const { id } = useDepositForm();
  const published = useSelector((state) =>
    isPublished(state.deposits[id].record)
  );
  return published || Boolean(extra);
}
