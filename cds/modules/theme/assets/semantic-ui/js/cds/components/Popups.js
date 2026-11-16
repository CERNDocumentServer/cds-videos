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
import { Popup } from "semantic-ui-react";

/** Tooltip on hover with an HTML content (``uib-tooltip-html``). */
export function Tooltip({ html, position, children }) {
  return (
    <Popup
      trigger={children}
      content={<span dangerouslySetInnerHTML={{ __html: html }} />}
      position={position}
      className="cds-tooltip"
      inverted
      size="mini"
      on="hover"
    />
  );
}

Tooltip.propTypes = {
  html: PropTypes.string.isRequired,
  position: PropTypes.string,
  children: PropTypes.element.isRequired,
};

Tooltip.defaultProps = { position: "top center" };

/**
 * Popover opened on click and closed when clicking outside (Bootstrap
 * ``rel="popover"`` links of the record page).
 */
export function Popover({ title, html, content, position, children }) {
  return (
    <Popup
      trigger={children}
      header={title || undefined}
      content={
        html ? <div dangerouslySetInnerHTML={{ __html: html }} /> : content
      }
      position={position}
      className="cds-popover"
      on="click"
    />
  );
}

Popover.propTypes = {
  title: PropTypes.string,
  html: PropTypes.string,
  content: PropTypes.node,
  position: PropTypes.string,
  children: PropTypes.element.isRequired,
};

Popover.defaultProps = {
  title: null,
  html: null,
  content: null,
  position: "bottom center",
};
