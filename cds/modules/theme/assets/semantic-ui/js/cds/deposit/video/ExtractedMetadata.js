/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Metadata extracted from the uploaded video, to copy into the form. */

import React, { useState } from "react";
import PropTypes from "prop-types";

import { DialogModal } from "@js/cds/shared/components/DialogModal";

import { useDeposit, useDepositActions } from "../state/hooks";
import { isPublished } from "../state/records";

/* Extracted metadata (``Fill metadata suggestion``) */

export function ExtractedMetadata({ id }) {
  const { record, metadataToFill } = useDeposit(id);
  const actions = useDepositActions(id);
  const [open, setOpen] = useState(false);
  const toDisplay = metadataToFill ? metadataToFill[1] : {};
  return !isPublished(record) ? (
    <div>
      {metadataToFill && (
        <div
          className="cds-alert cds-alert-warning cds-alert-dismissible cds-deposit-metadata-extraction-alert"
          role="alert"
        >
          <button
            type="button"
            className="cds-close"
            aria-label="Close"
            onClick={actions.dismissExtractedMetadata}
          >
            <span aria-hidden="true">&times;</span>
          </button>
          Extracted metadata can be used to automatically fill part of the form.{" "}
          <button
            type="button"
            className="ui small orange button pull-right"
            onClick={() => setOpen(true)}
          >
            See the extracted metadata
          </button>
        </div>
      )}
      <DialogModal
        open={open}
        onClose={() => setOpen(false)}
        title="Are you sure you want to use the following metadata?"
        buttons={[
          ["No", "basic", () => actions.fillMetadata(false)],
          ["Yes", "green", () => actions.fillMetadata(true)],
        ]}
      >
        <ul>
          {Object.entries(toDisplay).map(([key, value]) => (
            <li key={key}>
              <strong>{key}</strong>{" "}
              {typeof value === "string" ? value : JSON.stringify(value)}
            </li>
          ))}
        </ul>
      </DialogModal>
    </div>
  ) : null;
}

ExtractedMetadata.propTypes = { id: PropTypes.string.isRequired };
