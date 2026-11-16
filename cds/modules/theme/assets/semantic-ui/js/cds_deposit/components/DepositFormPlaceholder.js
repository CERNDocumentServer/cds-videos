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
 * Semantic UI placeholder of the deposit form, shown while an existing
 * project is loading. It has the panels of the form (project, then a video)
 * so the page keeps its shape when the project arrives.
 */

import React from "react";
import PropTypes from "prop-types";
import { Placeholder } from "semantic-ui-react";

/** A form field: its label and its input. */
function FieldPlaceholder({ tall }) {
  return (
    <Placeholder fluid className="cds-placeholder cds-placeholder-field">
      <Placeholder.Header>
        <Placeholder.Line length="very short" />
      </Placeholder.Header>
      <Placeholder.Image
        className={`cds-placeholder-input${
          tall ? " cds-placeholder-input-tall" : ""
        }`}
      />
    </Placeholder>
  );
}

FieldPlaceholder.propTypes = { tall: PropTypes.bool };
FieldPlaceholder.defaultProps = { tall: false };

function PanelPlaceholder({ icon, title, children }) {
  return (
    <div className="cds-panel cds-deposit-panel">
      <div className="cds-panel-heading text-muted px-20 py-10">
        <span className="text-muted">
          <i className={`fa ${icon}`} /> {title}
        </span>
      </div>
      <div className="cds-panel-body">{children}</div>
    </div>
  );
}

PanelPlaceholder.propTypes = {
  icon: PropTypes.string.isRequired,
  title: PropTypes.string.isRequired,
  children: PropTypes.node.isRequired,
};

export function DepositFormPlaceholder() {
  return (
    <div className="cds-deposit-placeholder" aria-busy="true">
      <div className="cds-deposit-avc-overall-status mb-20">
        <div className="cds-container-fluid">
          <Placeholder className="cds-placeholder cds-placeholder-text">
            <Placeholder.Header>
              <Placeholder.Line length="full" />
            </Placeholder.Header>
          </Placeholder>
        </div>
      </div>
      <div className="cds-container-fluid">
        <div className="cds-row">
          <div className="cds-col-md-12">
            <PanelPlaceholder icon="fa-list-ul" title="Project">
              <div className="cds-row">
                <div className="cds-col-sm-6">
                  <FieldPlaceholder />
                </div>
                <div className="cds-col-sm-6">
                  <FieldPlaceholder />
                </div>
              </div>
              <Placeholder className="cds-placeholder cds-placeholder-centered mt-20">
                <Placeholder.Paragraph>
                  <Placeholder.Line length="full" />
                  <Placeholder.Line length="full" />
                </Placeholder.Paragraph>
              </Placeholder>
            </PanelPlaceholder>
            <PanelPlaceholder icon="fa-video-camera" title="Video">
              <div className="cds-row">
                <div className="cds-col-sm-3">
                  <Placeholder fluid className="cds-placeholder">
                    <Placeholder.Image className="cds-placeholder-preview" />
                    <Placeholder.Paragraph>
                      <Placeholder.Line length="medium" />
                      <Placeholder.Line length="short" />
                      <Placeholder.Line length="long" />
                      <Placeholder.Line length="medium" />
                    </Placeholder.Paragraph>
                  </Placeholder>
                </div>
                <div className="cds-col-sm-9">
                  <Placeholder fluid className="cds-placeholder mb-20">
                    <Placeholder.Header>
                      <Placeholder.Line length="medium" />
                    </Placeholder.Header>
                  </Placeholder>
                  <FieldPlaceholder />
                  <FieldPlaceholder tall />
                </div>
              </div>
            </PanelPlaceholder>
          </div>
        </div>
      </div>
    </div>
  );
}
