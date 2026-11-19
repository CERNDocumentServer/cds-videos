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
import { useDispatch } from "react-redux";

import { DialogModal } from "@js/cds/shared/components/DialogModal";
import { prevent } from "@js/cds/shared/dom";

import { removeBackendError } from "../state/deposit";
import { authorFromUser, autocompleteAuthors } from "./autocomplete";
import { useDepositForm } from "./formContext";
import { SelectField } from "./BasicFields";
import { RemoteSelectField } from "./RemoteSelectField";
import { ArrayField } from "./ArrayField";

/* Information about custom authors */
export function CustomAuthorsInfo() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <a href="#info" onClick={prevent(() => setOpen(true))}>
        <i className="pull-right fa fa-info" />
      </a>
      <DialogModal
        open={open}
        onClose={() => setOpen(false)}
        title="Custom authors"
      >
        <p>
          Start by typing an author name and suggestions will become available
          to choose from.
        </p>
        <p>
          If you wish to enter a custom author please use this format:
          &quot;Lastname, Firstname&quot;
        </p>
      </DialogModal>
    </>
  );
}

/* Contributors */
export function ContributorsField({ roles }) {
  const { id } = useDepositForm();
  const dispatch = useDispatch();
  // The typed author is the "Add" item of the menu, not a suggestion
  const [fetchAuthors] = useState(() =>
    autocompleteAuthors("/api/ldap/cern-users/", { withUserInput: false })
  );
  return (
    <ArrayField
      name="contributors"
      label="Contributors"
      required
      add="Add another contributor"
      startEmpty={false}
      renderItem={(path) => (
        <>
          <CustomAuthorsInfo />
          <RemoteSelectField
            name={path}
            errorName={`${path}.name`}
            label="Name"
            placeholder="Author name"
            required
            fetchOptions={fetchAuthors}
            minLength={2}
            delay={500}
            toAddition={authorFromUser}
            hint={
              <>
                Search the CERN directory, or add someone else as{" "}
                <b>Lastname, Firstname</b>
              </>
            }
            onSelect={(item, setValue) => {
              // The whole contributor is replaced (as with ui-select)
              setValue(item.value);
              dispatch(removeBackendError(id, `${path}.name`));
            }}
          />
          <SelectField
            name={`${path}.role`}
            label="Role"
            options={roles}
            required
          />
        </>
      )}
    />
  );
}

ContributorsField.propTypes = { roles: PropTypes.array.isRequired };
