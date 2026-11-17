/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Details below the description of a video. */

import React from "react";
import PropTypes from "prop-types";

import { Tooltip } from "@js/cds/shared/components/Popups";
import { get, groupBy, isEmpty } from "@js/cds/shared/utils/collections";
import { formatRelationResourceType } from "@js/cds/shared/utils/text";
import { absoluteURL } from "@js/cds/shared/utils/urls";
import { isoToLanguage } from "@js/cds/shared/utils/languages";

/** Contributors, by role. */
export function Contributors({ record }) {
  const contributors = groupBy(record.metadata.contributors, "role");
  return (
    <div className="mb-20">
      <p>
        <strong>Contributors</strong>
      </p>
      {Object.entries(contributors).map(([role, contribs]) => (
        <div className="pl-10" key={role}>
          <p>{role}: </p>
          <ul>
            {contribs.map((contrib, index) => (
              <li key={index}>
                <a href={`/search?q=contributors.name:"${contrib.name}"`}>
                  {contrib.name}
                </a>{" "}
                {contrib.affiliations
                  ? " - " + contrib.affiliations.join(",")
                  : ""}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

Contributors.propTypes = { record: PropTypes.object.isRequired };

/** Licences of the CERN material, when there are several licences. */
export function Licences({ record }) {
  const metadata = record.metadata;
  const licenses = groupBy(metadata.license, "material", "other");
  if (!((metadata.license || []).length > 1)) {
    return null;
  }
  return (
    <div className="mb-0">
      <p>
        <strong>Licences</strong>
      </p>
      {Object.entries(licenses)
        .filter(([material]) => material !== "other")
        .map(([material, items]) => (
          <div className="pl-10" key={material}>
            <p>{material}:</p>
            <ul>
              {items
                .filter((license) => license.license || license.credit)
                .map((license, index) => (
                  <li key={index}>
                    {license.credit && <span>{license.credit}</span>}
                    {!license.credit && license.license && (
                      <span>
                        <a target="_blank" rel="noreferrer" href={license.url}>
                          {license.license}
                        </a>
                      </span>
                    )}
                  </li>
                ))}
            </ul>
          </div>
        ))}
    </div>
  );
}

Licences.propTypes = { record: PropTypes.object.isRequired };

/** Language of the video and link to the other videos of its project. */
export function LanguageAndProject({ record }) {
  const metadata = record.metadata;
  return (
    <div className="mt-30">
      <ul className="cds-list-inline pt-20 f8">
        {metadata.language && (
          <Tooltip html="Video Language">
            <li>
              <i className="fa fa-globe text-muted" />{" "}
              <a href={`/search?q=language:"${metadata.language}"`}>
                {isoToLanguage(metadata.language)}
              </a>
            </li>
          </Tooltip>
        )}{" "}
        {metadata.language &&
          (get(record, "links.project_html") || metadata._project_id) && (
            <li>·</li>
          )}{" "}
        {(get(record, "links.project_html") || metadata._project_id) && (
          <li>
            <i className="fa fa-list-ul text-muted" />{" "}
            <a
              href={
                get(record, "links.project_html") ||
                "/search?q=_project_id:" + metadata._project_id
              }
            >
              More videos in the project
            </a>
          </li>
        )}
      </ul>
    </div>
  );
}

LanguageAndProject.propTypes = { record: PropTypes.object.isRequired };

export function RelatedLinks({ record }) {
  const metadata = record.metadata;
  if (!((metadata.related_links || []).length > 0)) {
    return null;
  }
  return (
    <div>
      <strong>Related links</strong>
      {metadata.related_links.map((relatedLink, index) => (
        <ul key={index}>
          <li>
            <a
              href={absoluteURL(relatedLink.url)}
              target="_blank"
              rel="noreferrer"
            >
              {relatedLink.name}
            </a>
          </li>
        </ul>
      ))}
    </div>
  );
}

RelatedLinks.propTypes = { record: PropTypes.object.isRequired };

/** Related identifiers, grouped by relation type. */
export function RelatedIdentifiers({ groupedRelatedIdentifiers }) {
  if (isEmpty(groupedRelatedIdentifiers)) {
    return null;
  }
  return (
    <div>
      <strong>Related identifiers</strong>
      <ul>
        {Object.entries(groupedRelatedIdentifiers).map(
          ([relationType, items]) => (
            <li key={relationType}>
              <strong>{formatRelationResourceType(relationType)}</strong>
              <ul>
                {items.map((ri, index) => (
                  <li key={index}>
                    {ri.resource_type && (
                      <span>
                        {formatRelationResourceType(ri.resource_type)}:{" "}
                      </span>
                    )}
                    <a
                      className="cds-text-break"
                      href={ri.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {ri.identifier}
                    </a>{" "}
                    ({ri.scheme})
                  </li>
                ))}
              </ul>
            </li>
          )
        )}
      </ul>
    </div>
  );
}

RelatedIdentifiers.propTypes = {
  groupedRelatedIdentifiers: PropTypes.object.isRequired,
};
