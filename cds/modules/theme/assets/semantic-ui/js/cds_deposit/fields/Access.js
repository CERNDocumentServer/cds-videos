/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* Access restrictions and editors of the deposits (``cdsForm``). */

import React from "react";
import PropTypes from "prop-types";
import _get from "lodash/get";
import { useSelector } from "react-redux";

import {
  useAccessRights,
  useDeposit,
  useDepositActions,
  useProjectRecord,
} from "../state/hooks";
import { isPublished } from "../state/records";

import { AsyncMultiSelect } from "./AsyncSelect";
import { autocompleteAccess } from "./autocomplete";

function noResultsMessage(query) {
  return (
    <p className="pa-5 mb-0">
      {query ? (
        <span>Not results for &quot;{query}&quot;</span>
      ) : (
        <span>Start typing a name ...</span>
      )}
    </p>
  );
}

/** E-mails of people or e-groups (``ui-select`` of the access fields). */
/** The e-mail of a value (an e-mail, possibly empty, or a suggestion). */
function emailOf(item) {
  return item !== null && typeof item === "object" ? item.email : item;
}

export function EmailsSelect({
  values = [],
  onChange,
  disabled = false,
  delay = 100,
  lockedValues = [],
}) {
  const emails = values || [];
  return (
    <AsyncMultiSelect
      values={emails.map((email) => ({ email, name: email }))}
      getName={emailOf}
      toItem={(email) => ({ email, name: email })}
      fetchOptions={autocompleteAccess}
      minLength={0}
      delay={delay}
      disabled={disabled}
      placeholder="Enter personal emails or e-group emails here"
      noResultsMessage={noResultsMessage}
      lockedValues={lockedValues}
      renderResult={(item) => (
        <>
          <div>{item.name}</div>
          {!item.isUserInput && <small>&lt;{item.email}&gt;</small>}
        </>
      )}
      onChange={(items) => onChange(items.map(emailOf))}
    />
  );
}

EmailsSelect.propTypes = {
  values: PropTypes.array,
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  delay: PropTypes.number,
  lockedValues: PropTypes.array,
};

/** "Project restrictions when published" and "Published video restrictions". */
export function RestrictionsBox({ id, project = false }) {
  const { record, permissions } = useDeposit(id);
  const actions = useDepositActions(id);
  const access = _get(useAccessRights(), "metadata.access") || {};
  const projectRecord = useProjectRecord();
  const published = isPublished(record);
  const hasCategory = project
    ? Boolean(record.category)
    : Boolean(projectRecord.category);
  const restrictedLocked = access.restricted || [];
  return (
    <div className="cds-alert cds-alert-info">
      <h4>
        {project
          ? "Project restrictions when published"
          : "Published video restrictions"}
      </h4>
      <small>
        {project
          ? "Change if the published project should be public or restricted"
          : "Change if the published video should be public or restricted"}
      </small>
      <div style={{ display: hasCategory ? undefined : "none" }}>
        <select
          className="cds-form-control"
          value={permissions || ""}
          disabled={!access.public || published}
          onChange={(e) => actions.setPermissions(e.target.value)}
        >
          {!permissions && <option value="" />}
          <option value="public">Public</option>
          <option value="restricted">Restricted</option>
        </select>
        <div
          className="restricted mt-20"
          style={{
            display: permissions === "restricted" ? undefined : "none",
          }}
        >
          <label className="control-label">
            {project
              ? "Choose who can access the published project"
              : "Choose who can access the published video and watch it"}
          </label>
          {!project && (
            <div>
              <small>
                Restrictions are <strong>not</strong> inherited from the project
                and can be set independently
              </small>
            </div>
          )}
          <EmailsSelect
            values={_get(record, "_access.read") || []}
            disabled={
              (!record.category && access.public === "public") || published
            }
            lockedValues={restrictedLocked}
            onChange={(emails) => actions.setAccess("_access.read", emails)}
          />
        </div>
      </div>
      <div style={{ display: hasCategory ? "none" : undefined }}>
        {project
          ? "Please select a category from the Basic Info tab."
          : "Please select a category for the project."}
      </div>
    </div>
  );
}

RestrictionsBox.propTypes = {
  id: PropTypes.string.isRequired,
  project: PropTypes.bool,
};

/** "Project editors" tab. */
export function EditorsField({ id }) {
  const record = useSelector((state) => state.deposits[id].record);
  const actions = useDepositActions(id);
  return (
    <div className="cds-row">
      <div className="cds-col-sm-12">
        <h4>Grant edit access to the project and the videos</h4>
        <small>
          Choose who can access and edit this project and all videos
        </small>
        <EmailsSelect
          values={_get(record, "_access.update") || []}
          disabled={isPublished(record)}
          delay={500}
          onChange={(emails) => actions.setAccess("_access.update", emails)}
        />
      </div>
    </div>
  );
}

EditorsField.propTypes = { id: PropTypes.string.isRequired };
