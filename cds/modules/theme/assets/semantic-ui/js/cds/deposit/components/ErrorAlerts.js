/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

import React from "react";
import PropTypes from "prop-types";

import { useDeposit, useDepositActions } from "../state/hooks";

/** Validation errors returned by the server (``alert alert-danger``). */
export function ErrorAlerts({ id }) {
  const { alerts } = useDeposit(id);
  const { dismissAlert } = useDepositActions(id);
  return alerts.map((alert, index) => (
    // eslint-disable-next-line react/no-array-index-key
    <div className="alerts" key={index}>
      {alert.errors && alert.errors.length > 0 && alert.type === "danger" && (
        <div>
          <div
            className="cds-alert cds-alert-danger cds-alert-dismissible"
            role="alert"
          >
            <button
              type="button"
              className="cds-close"
              onClick={() => dismissAlert(index)}
            >
              <span aria-hidden="true">&times;</span>
              <span className="sr-only">Close</span>
            </button>
            <div>
              <strong>{alert.message}</strong>
              <ul>
                {alert.errors.map((error, errorIndex) => (
                  // eslint-disable-next-line react/no-array-index-key
                  <li key={errorIndex}>
                    <b>{error.field}</b> {error.message}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  ));
}

ErrorAlerts.propTypes = { id: PropTypes.string.isRequired };
