/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* Groups of fields of the "Licences", "Translations" and "Related information" tabs. */

import React from "react";
import PropTypes from "prop-types";

import {
  ArrayField,
  Fieldset,
  SelectField,
  TextAreaField,
  TextField,
} from "./Fields";
import {
  SCHEMA_DESCRIPTIONS,
  PROJECT_TRANSLATION_LANGUAGES,
  RELATED_IDENTIFIER_SCHEMES,
  RELATION_TYPES,
  RESOURCE_TYPES,
  VIDEO_TRANSLATION_LANGUAGES,
} from "./options";

/** Metadata translations. */
export function TranslationsField({ project = false }) {
  return (
    <ArrayField
      name="translations"
      label="Add metadata translations"
      add="Add translations"
      // Default value of the schema
      newItem={() => ({ language: "en" })}
      renderItem={(path) => (
        <>
          <TextField name={`${path}.title.title`} label="Title" />
          <TextAreaField
            name={`${path}.description`}
            label="Description"
            description={SCHEMA_DESCRIPTIONS["translations.description"]}
          />
          <SelectField
            name={`${path}.language`}
            label="Language"
            description={SCHEMA_DESCRIPTIONS["translations.language"]}
            options={
              project
                ? PROJECT_TRANSLATION_LANGUAGES
                : VIDEO_TRANSLATION_LANGUAGES
            }
          />
        </>
      )}
    />
  );
}

TranslationsField.propTypes = { project: PropTypes.bool };

/** Copyright of a video. */
export function CopyrightFieldset() {
  return (
    <Fieldset title="Copyright">
      <TextField
        name="copyright.holder"
        label="Holder"
        description={SCHEMA_DESCRIPTIONS["copyright.holder"]}
      />
      <TextField
        name="copyright.year"
        label="Year"
        description={SCHEMA_DESCRIPTIONS["copyright.year"]}
      />
      <TextField name="copyright.url" label="URL" />
    </Fieldset>
  );
}

/** Related links of a video. */
export function RelatedLinksField() {
  return (
    <ArrayField
      name="related_links"
      label="Related links information"
      add="Add related links"
      renderItem={(path) => (
        <>
          <TextField name={`${path}.name`} label="Name" />
          <TextField name={`${path}.url`} label="URL" />
        </>
      )}
    />
  );
}

/** Related identifiers of a video. */
export function RelatedIdentifiersField() {
  return (
    <ArrayField
      name="related_identifiers"
      label="Related Identifiers"
      add="Add related identifiers"
      description="Add identifiers for related resources such as DOIs, URLs, or Indico event IDs."
      renderItem={(path) => (
        <>
          <TextField
            name={`${path}.identifier`}
            label="Identifier"
            required
            placeholder="e.g., 10.1234/example.doi, https://example.com, 12345"
            description="The identifier value (DOI, URL, or Indico event ID)"
          />
          <SelectField
            name={`${path}.scheme`}
            label="Scheme"
            required
            options={RELATED_IDENTIFIER_SCHEMES}
            description="The type of identifier scheme"
          />
          <SelectField
            name={`${path}.relation_type`}
            label="Relation Type"
            required
            options={RELATION_TYPES}
            description="How this resource relates to the identified resource"
          />
          <SelectField
            name={`${path}.resource_type`}
            label="Resource Type"
            options={RESOURCE_TYPES}
            description="The type of the related resource (optional)"
          />
        </>
      )}
    />
  );
}
