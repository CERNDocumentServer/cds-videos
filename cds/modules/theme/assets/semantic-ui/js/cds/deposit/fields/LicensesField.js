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

import { autocompleteLicenses } from "./autocomplete";
import { TextField } from "./BasicFields";
import { RemoteSelectField } from "./RemoteSelectField";
import { ArrayField } from "./ArrayField";

/* Licences */
export function LicensesField() {
  return (
    <ArrayField
      name="license"
      notitle
      firstItemMessage="General license"
      add="Add licences"
      inline
      renderItem={(path, index) => (
        <>
          <RemoteSelectField
            name={`${path}.license`}
            label="Licence"
            placeholder="Search for a license name..."
            fetchOptions={autocompleteLicenses}
            minLength={1}
            delay={100}
          />
          {index !== 0 && (
            <TextField
              name={`${path}.material`}
              label="Material"
              placeholder="Material"
            />
          )}
          <TextField
            name={`${path}.credit`}
            label="Credit"
            placeholder="Credit"
          />
        </>
      )}
    />
  );
}
