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

/**
 * Dialog with a title and a close button, rendered in place with the markup
 * and the styles of the former ``modal-dialog`` (ngModal) directive.
 */
export function DialogModal({
  open,
  onClose,
  title = null,
  children = null,
  className = null,
}) {
  return (
    <div
      className={["ng-modal", className].filter(Boolean).join(" ")}
      style={{ display: open ? undefined : "none" }}
    >
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions */}
      <div className="ng-modal-overlay" onClick={onClose} />
      <div className="ng-modal-dialog">
        <span
          className="ng-modal-title"
          style={{ display: title ? undefined : "none" }}
        >
          {title}
        </span>
        {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions */}
        <div className="ng-modal-close" onClick={onClose}>
          <div>
            <span className="ng-modal-close-x">X</span>
          </div>
        </div>
        <div className="ng-modal-dialog-content">{open && children}</div>
      </div>
    </div>
  );
}

DialogModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  title: PropTypes.node,
  children: PropTypes.node,
  className: PropTypes.string,
};
