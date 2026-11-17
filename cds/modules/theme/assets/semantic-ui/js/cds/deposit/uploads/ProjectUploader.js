/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Files of the project: the master videos with their formats and frames. */

import React, { useState } from "react";
import PropTypes from "prop-types";
import clsx from "clsx";

import { filterByText } from "@js/cds/shared/utils/collections";
import { prevent } from "@js/cds/shared/dom";

import { useDeposit, useDepositActions } from "../state/hooks";
import { findMasterFile, isPublished } from "../state/records";
import { thumbnailPreview } from "../state/uploads";
import { DropZone } from "./DropZone";
import { TipsBox } from "../components/TipsBox";
import {
  FileName,
  SearchRow,
  FileSize,
  FileProgress,
  RemoveLink,
  SortHeader,
  sortFiles,
} from "./FileTable";
import { HowToUpdateDialog, ReplaceMasterDialog } from "./UploadDialogs";

/** Files of the project. */
export function ProjectUploader({ id }) {
  const { record } = useDeposit(id);
  const actions = useDepositActions(id);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState({ type: undefined, reverse: false });
  const [showSubformats, setShowSubformats] = useState(false);
  const [showFrames, setShowFrames] = useState(false);
  const files = record._files || [];
  const visible = filterByText(sortFiles(files, sort), search);
  const master = findMasterFile(record) || {};
  const published = isPublished(record);
  return (
    <>
      <ReplaceMasterDialog
        id={id}
        message={(name) =>
          `Are you sure you want to replace the uploaded video with ${name}?`
        }
      />
      {files.length > 0 && (
        <div className="cds-panel">
          <div className="cds-panel-heading">
            <SearchRow files={files} search={search} setSearch={setSearch} />
          </div>
          <table className="cds-table">
            <tbody>
              <tr>
                <SortHeader
                  label="Filename"
                  field="key"
                  sort={sort}
                  setSort={setSort}
                />
                <SortHeader
                  label="Size"
                  field="size"
                  sort={sort}
                  setSort={setSort}
                />
                <th className="text-center">Progress</th>
                <th className="text-center">Actions</th>
              </tr>
              {visible.map((file, index) => (
                <tr
                  // eslint-disable-next-line react/no-array-index-key
                  key={`${file.key}-${index}`}
                  className={clsx(
                    "sel-file",
                    file.context_type === "master" && "active"
                  )}
                >
                  <FileName file={file} />
                  <FileSize file={file} />
                  <FileProgress file={file} done="✓" />
                  <td className="text-center">
                    {!(
                      file.context_type === "master" || file.percentage < 100
                    ) && (
                      <RemoveLink onRemove={actions.removeFile} file={file} />
                    )}
                    {(file.context_type === "master" ||
                      file.percentage < 100) && (
                      <span>
                        <HowToUpdateDialog />
                      </span>
                    )}
                  </td>
                </tr>
              ))}
              {visible.length === 0 && (
                <tr>
                  <td colSpan="4" className="text-center text-muted">
                    {" "}
                    No results.
                  </td>
                </tr>
              )}
              {(master.subformat || []).length > 0 && (
                <tr className="warning">
                  <td>Extracted subformats</td>
                  <td />
                  <td className="text-center" />
                  <td className="text-center">
                    <a
                      href="#subformats"
                      onClick={prevent(() =>
                        setShowSubformats(!showSubformats)
                      )}
                    >
                      {showSubformats ? <span>Hide</span> : <span>Show</span>}
                    </a>
                  </td>
                </tr>
              )}
              {(master.subformat || [])
                .filter((f) => f.key)
                .map((f) =>
                  showSubformats ? (
                    <tr key={f.key} className="sel-file">
                      <FileName file={f} />
                      <td />
                      <td className="text-center">
                        {f.percentage > 0 &&
                          !f.status_completed &&
                          !f.status_failure && (
                            <span>{toInt(f.percentage)} %</span>
                          )}
                        {!f.percentage &&
                          !f.status_completed &&
                          !f.status_failure && (
                            <span>
                              <i className="fa fa-spinner fa-spin" />
                            </span>
                          )}
                        {f.status_failure && (
                          <span className="text-danger">Error</span>
                        )}
                        {f.status_completed && !f.status_failure && (
                          <span className="text-success">✓</span>
                        )}
                      </td>
                    </tr>
                  ) : null
                )}
              {master.frame && (
                <tr className="warning">
                  <td>Extracted frames</td>
                  <td />
                  <td />
                  <td className="text-center">
                    <a
                      href="#frames"
                      onClick={prevent(() => setShowFrames(!showFrames))}
                    >
                      {showFrames ? <span>Hide</span> : <span>Show</span>}
                    </a>
                  </td>
                </tr>
              )}
              {showFrames && (
                <tr>
                  <td colSpan="4">
                    <div className="cds-row cds-deposit-thumbnail-pad">
                      {(master.frame || []).map((frame) => (
                        <div
                          className="cds-deposit-frame-thumbnail"
                          key={frame.key}
                        >
                          <a
                            href={frame.links && frame.links.self}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {showFrames && (
                              <img
                                width="100%"
                                alt=""
                                src={thumbnailPreview(frame)}
                              />
                            )}
                          </a>
                        </div>
                      ))}
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
      <hr className="my-20" />
      {!published && (
        <div className="cds-deposit-box">
          <DropZone multiple onFiles={actions.addFiles}>
            <div className="pa-10 cds-deposit-box-upload-wrapper text-center">
              <p className="cds-deposit-box-upload-icon mb-20">
                <i className="fa fa-3x fa-files-o" aria-hidden="true" />
              </p>
              <div className="cds-deposit-box-upload-content">
                <div className="cds-deposit-box-upload-title">
                  <h4>Upload additional files for this project</h4>
                </div>
                <p className="cds-deposit-box-upload-description">
                  {" "}
                  Or Drag &amp; Drop files
                </p>
              </div>
            </div>
          </DropZone>
          <hr className="my-10" />
          <TipsBox>
            <li>You can upload files related to the project.</li>
          </TipsBox>
        </div>
      )}
      {published && (
        <TipsBox className="cds-deposit-box text-muted">
          <li>
            Click the <strong>Edit Project</strong> button on the bottom right
            corner to add more files.
          </li>
        </TipsBox>
      )}
    </>
  );
}

ProjectUploader.propTypes = { id: PropTypes.string.isRequired };

export function toInt(input) {
  const result = parseInt(input, 10);
  return isNaN(result) ? input : result;
}
