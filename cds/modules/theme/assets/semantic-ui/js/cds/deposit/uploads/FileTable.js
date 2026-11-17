/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Parts of the file tables of the uploaders. */

import React from "react";
import PropTypes from "prop-types";
import _orderBy from "lodash/orderBy";

import { bytesToHumanReadable } from "@js/cds/shared/utils/text";
import { prevent } from "@js/cds/shared/dom";

function truncate(text, length) {
  return (text || "").slice(0, length);
}

export function FileName({ file, children = null }) {
  return (
    <td title={file.key}>
      {truncate(file.key, 40)}{" "}
      {(file.key || "").length > 40 && <span>...</span>}
      {children}
    </td>
  );
}

FileName.propTypes = {
  file: PropTypes.object.isRequired,
  children: PropTypes.node,
};

export const FILES_HEADER = (
  <tr>
    <th>Filename</th>
    <th>Size</th>
    <th className="text-center">Progress</th>
    <th className="text-center">Actions</th>
  </tr>
);

export function SearchRow({ files, search, setSearch }) {
  return (
    <div className="cds-row">
      <div className="cds-col-sm-6">
        {files.length > 0 && <p className="text-muted" />}
      </div>
      <div className="cds-col-sm-12">
        <div className="form-group">
          <input
            type="text"
            className="cds-form-control input-sm"
            placeholder="Search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>
    </div>
  );
}

SearchRow.propTypes = {
  files: PropTypes.array.isRequired,
  search: PropTypes.string.isRequired,
  setSearch: PropTypes.func.isRequired,
};

/** Drop zone content of the video uploads. */
export function UploadBox({ icon, title }) {
  return (
    <div className="pa-10 cds-deposit-box-upload-wrapper text-center">
      <p className="cds-deposit-box-upload-icon mb-20">
        <i className={`fa ${icon}`} aria-hidden="true" />
      </p>
      <div className="cds-deposit-box-upload-content">
        <h4>{title}</h4>
        <p className="cds-deposit-box-upload-description">
          Or Drag &amp; Drop files
        </p>
      </div>
    </div>
  );
}

UploadBox.propTypes = {
  icon: PropTypes.string.isRequired,
  title: PropTypes.string.isRequired,
};

export function FileSize({ file }) {
  return (
    <td>
      {file.size !== undefined ? (
        <span>{bytesToHumanReadable(file.size)}</span>
      ) : (
        <span>Unknown</span>
      )}
    </td>
  );
}

FileSize.propTypes = { file: PropTypes.object.isRequired };

export function FileProgress({ file, done }) {
  return (
    <td className="text-center">
      {file.percentage < 100 && !file.status_failure && (
        <span>{file.percentage} %</span>
      )}
      {(file.status_pending || file.status_started) && (
        <span>Processing...</span>
      )}
      {file.status_failure && <span className="text-danger">Error</span>}
      {(file.status_completed || file.percentage === 100) &&
        !file.status_failure && <span className="text-success">{done}</span>}
    </td>
  );
}

FileProgress.propTypes = {
  file: PropTypes.object.isRequired,
  done: PropTypes.string.isRequired,
};

export function RemoveLink({ onRemove, file }) {
  return (
    <a href="#remove" onClick={prevent(() => onRemove(file.key))}>
      <i className="fa fa-trash-o" />
    </a>
  );
}

RemoveLink.propTypes = {
  onRemove: PropTypes.func.isRequired,
  file: PropTypes.object.isRequired,
};

export function SortHeader({ label, field, sort, setSort }) {
  return (
    <th>
      <a
        href="#sort"
        onClick={prevent(() =>
          setSort({ type: field, reverse: !sort.reverse })
        )}
      >
        {label}{" "}
        {sort.type === field && !sort.reverse && (
          <span className="fa fa-caret-down" />
        )}
        {sort.type === field && sort.reverse && (
          <span className="fa fa-caret-up" />
        )}
      </a>
    </th>
  );
}

SortHeader.propTypes = {
  label: PropTypes.string.isRequired,
  field: PropTypes.string.isRequired,
  sort: PropTypes.object.isRequired,
  setSort: PropTypes.func.isRequired,
};

export function sortFiles(files, sort) {
  if (!sort.type) {
    return files;
  }
  return _orderBy(files, [sort.type], [sort.reverse ? "desc" : "asc"]);
}
