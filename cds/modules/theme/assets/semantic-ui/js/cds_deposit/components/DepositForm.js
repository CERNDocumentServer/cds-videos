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
 * Formik form of a deposit: the values are the form fields of its record.
 * The fields write to the record, and the form takes the changes made to
 * the record by the page (``formSync``) or is reset to it (``formReset``).
 */

import React, { useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import { Formik, useFormikContext } from "formik";
import { useDispatch, useSelector, useStore } from "react-redux";

import { DepositFormContext } from "../fields/Fields";
import { validateProject, validateVideo } from "../fields/validation";
import { setFormErrors } from "../state/deposit";
import { formValues } from "../state/records";

/** Run ``effect`` when ``counter`` changes, not when the form is created. */
function useCounterEffect(counter, effect) {
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    effect();
    // Only the counter triggers it
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [counter]);
}

function FormBridge({ id, type, children }) {
  const formik = useFormikContext();
  const dispatch = useDispatch();
  const store = useStore();
  const formSync = useSelector((state) => state.deposits[id].formSync);
  const formReset = useSelector((state) => state.deposits[id].formReset);
  const values = () => formValues(store.getState().deposits[id].record, type);

  useCounterEffect(formSync, () => formik.setValues(values(), true));
  useCounterEffect(formReset, () => {
    const next = values();
    formik.resetForm({ values: next });
    formik.validateForm(next);
  });

  useEffect(() => {
    dispatch(setFormErrors(id, formik.errors));
  }, [dispatch, id, formik.errors]);

  const context = useMemo(() => ({ id, type }), [id, type]);
  return (
    <DepositFormContext.Provider value={context}>
      {children}
    </DepositFormContext.Provider>
  );
}

FormBridge.propTypes = {
  id: PropTypes.string.isRequired,
  type: PropTypes.string.isRequired,
  children: PropTypes.node,
};

FormBridge.defaultProps = { children: null };

export function DepositForm({ id, children }) {
  const store = useStore();
  const type = useSelector((state) => state.deposits[id].type);
  const [initialValues] = useState(() =>
    formValues(store.getState().deposits[id].record, type)
  );
  return (
    <Formik
      initialValues={initialValues}
      validate={type === "project" ? validateProject : validateVideo}
      validateOnMount
      onSubmit={() => {}}
    >
      <FormBridge id={id} type={type}>
        {children}
      </FormBridge>
    </Formik>
  );
}

DepositForm.propTypes = {
  id: PropTypes.string.isRequired,
  children: PropTypes.node,
};

DepositForm.defaultProps = { children: null };
