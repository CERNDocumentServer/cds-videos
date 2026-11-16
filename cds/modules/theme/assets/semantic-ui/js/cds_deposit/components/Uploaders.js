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
 * Files of the deposits (static/templates/cds_deposit/types/common/
 * uploader.html and types/video/uploader.html).
 */

import React, { useState } from "react";
import PropTypes from "prop-types";
import _orderBy from "lodash/orderBy";

import { DialogModal } from "@js/cds/components/DialogModal";
import { Tooltip } from "@js/cds/components/Popups";
import {
  angularFilter,
  bytesToHumanReadable,
  findBy,
  removeBy,
} from "@js/cds/utils";

import { toInt } from "../filters";
import {
  useConfig,
  useDeposit,
  useDepositActions,
  useStarted,
} from "../state/hooks";
import { findMasterFile, isPublished } from "../state/records";
import {
  startUploads,
  thumbnailPreview,
  validateAdditionalFiles,
  validateSubtitles,
} from "../state/uploads";
import { DropZone } from "./DropZone";
import { InfoDialog, show } from "./common";

function limitTo(text, length) {
  return (text || "").slice(0, length);
}

function FileName({ file }) {
  return (
    <td title={file.key}>
      {limitTo(file.key, 40)}{" "}
      <span
        style={{ display: (file.key || "").length > 40 ? undefined : "none" }}
      >
        ...
      </span>
    </td>
  );
}

FileName.propTypes = { file: PropTypes.object.isRequired };

function FileSize({ file }) {
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

function FileProgress({ file, done }) {
  return (
    <td className="text-center">
      <span style={show(file.percentage < 100 && !file.status_failure)}>
        {file.percentage} %
      </span>
      <span style={show(file.status_pending || file.status_started)}>
        Processing...
      </span>
      <span style={show(file.status_failure)} className="text-danger">
        Error
      </span>
      <span
        style={show(
          (file.status_completed || file.percentage === 100) &&
            !file.status_failure
        )}
        className="text-success"
      >
        {done}
      </span>
    </td>
  );
}

FileProgress.propTypes = {
  file: PropTypes.object.isRequired,
  done: PropTypes.string.isRequired,
};

function HowToUpdateDialog() {
  return (
    <InfoDialog
      title="How to update the video file"
      trigger={(open) => (
        <a
          href="#info"
          onClick={(e) => {
            e.preventDefault();
            open();
          }}
        >
          <i className="fa fa-info" />
        </a>
      )}
    >
      <p className="text-left">
        To replace the video file, just upload another video file.
      </p>
    </InfoDialog>
  );
}

function RemoveLink({ onRemove, file }) {
  return (
    <a
      href="#remove"
      onClick={(e) => {
        e.preventDefault();
        onRemove(file.key);
      }}
    >
      <i className="fa fa-trash-o" />
    </a>
  );
}

RemoveLink.propTypes = {
  onRemove: PropTypes.func.isRequired,
  file: PropTypes.object.isRequired,
};

function ReplaceMasterDialog({ id, message }) {
  const { newMasterName } = useDeposit(id);
  const { closeNewMasterDialog } = useDepositActions(id);
  return (
    <DialogModal
      open={newMasterName !== null}
      onClose={() => closeNewMasterDialog(false)}
      title="Replace master file"
    >
      <p>{message(newMasterName)}</p>
      <hr className="mt-30 mb-10" />
      <p className="pull-right">
        <button
          type="button"
          className="ui basic button"
          onClick={() => closeNewMasterDialog(false)}
        >
          Cancel
        </button>
        <button
          type="button"
          className="ui green button"
          onClick={() => closeNewMasterDialog(true)}
        >
          Yes
        </button>
      </p>
      <div className="cds-clearfix" />
    </DialogModal>
  );
}

ReplaceMasterDialog.propTypes = {
  id: PropTypes.string.isRequired,
  message: PropTypes.func.isRequired,
};

function SortHeader({ label, field, sort, setSort }) {
  return (
    <th>
      <a
        href="#sort"
        onClick={(e) => {
          e.preventDefault();
          setSort({ type: field, reverse: !sort.reverse });
        }}
      >
        {label}{" "}
        <span
          style={show(sort.type === field && !sort.reverse)}
          className="fa fa-caret-down"
        />
        <span
          style={show(sort.type === field && sort.reverse)}
          className="fa fa-caret-up"
        />
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

function sortFiles(files, sort) {
  if (!sort.type) {
    return files;
  }
  return _orderBy(files, [sort.type], [sort.reverse ? "desc" : "asc"]);
}

function TipsBox({ children }) {
  return (
    <div className="text-muted">
      <h5 className="text-muted">
        <strong>Tips and suggestions</strong>
      </h5>
      <ul>{children}</ul>
    </div>
  );
}

TipsBox.propTypes = { children: PropTypes.node.isRequired };

/** Files of the project (``types/common/uploader.html``). */
export function ProjectUploader({ id }) {
  const { record } = useDeposit(id);
  const actions = useDepositActions(id);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState({ type: undefined, reverse: false });
  const [showSubformats, setShowSubformats] = useState(false);
  const [showFrames, setShowFrames] = useState(false);
  const files = record._files || [];
  const visible = angularFilter(sortFiles(files, sort), search);
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
      <div className="cds-panel" style={show(files.length > 0)}>
        <div className="cds-panel-heading">
          <div className="cds-row">
            <div className="cds-col-sm-6">
              <p style={show(files.length > 0)} className="text-muted" />
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
                className={[
                  "sel-file",
                  file.context_type === "master" && "active",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                <FileName file={file} />
                <FileSize file={file} />
                <FileProgress file={file} done="✓" />
                <td className="text-center">
                  {!(
                    file.context_type === "master" || file.percentage < 100
                  ) && <RemoveLink onRemove={actions.removeFile} file={file} />}
                  <span
                    style={show(
                      file.context_type === "master" || file.percentage < 100
                    )}
                  >
                    <HowToUpdateDialog />
                  </span>
                </td>
              </tr>
            ))}
            <tr style={show(visible.length === 0)}>
              <td colSpan="4" className="text-center text-muted">
                {" "}
                No results.
              </td>
            </tr>
            <tr
              className="warning"
              style={show((master.subformat || []).length > 0)}
            >
              <td>Extracted subformats</td>
              <td />
              <td className="text-center" />
              <td className="text-center">
                <a
                  href="#subformats"
                  onClick={(e) => {
                    e.preventDefault();
                    setShowSubformats(!showSubformats);
                  }}
                >
                  {showSubformats ? <span>Hide</span> : <span>Show</span>}
                </a>
              </td>
            </tr>
            {(master.subformat || [])
              .filter((f) => f.key)
              .map((f) => (
                <tr
                  key={f.key}
                  className="sel-file"
                  style={show(showSubformats)}
                >
                  <FileName file={f} />
                  <td />
                  <td className="text-center">
                    {f.percentage > 0 &&
                      !f.status_completed &&
                      !f.status_failure && <span>{toInt(f.percentage)} %</span>}
                    {!f.percentage &&
                      !f.status_completed &&
                      !f.status_failure && (
                        <span>
                          <i className="fa fa-spinner fa-spin" />
                        </span>
                      )}
                    <span
                      style={show(f.status_failure)}
                      className="text-danger"
                    >
                      Error
                    </span>
                    <span
                      style={show(f.status_completed && !f.status_failure)}
                      className="text-success"
                    >
                      ✓
                    </span>
                  </td>
                </tr>
              ))}
            <tr className="warning" style={show(master.frame)}>
              <td>Extracted frames</td>
              <td />
              <td />
              <td className="text-center">
                <a
                  href="#frames"
                  onClick={(e) => {
                    e.preventDefault();
                    setShowFrames(!showFrames);
                  }}
                >
                  {showFrames ? <span>Hide</span> : <span>Show</span>}
                </a>
              </td>
            </tr>
            <tr style={show(showFrames)}>
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
          </tbody>
        </table>
      </div>
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
        <div className="cds-deposit-box text-muted">
          <h5 className="text-muted">
            <strong>Tips and suggestions</strong>
          </h5>
          <ul>
            <li>
              Click the <strong>Edit Project</strong> button on the bottom right
              corner to add more files.
            </li>
          </ul>
        </div>
      )}
    </>
  );
}

ProjectUploader.propTypes = { id: PropTypes.string.isRequired };

function AddLink({ onFiles, accept, pattern, validate, multiple }) {
  return (
    <DropZone
      as="a"
      className="cds-add-link"
      droppable={false}
      multiple={multiple}
      accept={accept}
      pattern={pattern}
      validate={validate}
      onFiles={onFiles}
    >
      <i className="fa fa-plus-square" />
    </DropZone>
  );
}

AddLink.propTypes = {
  onFiles: PropTypes.func.isRequired,
  accept: PropTypes.string,
  pattern: PropTypes.string,
  validate: PropTypes.func,
  multiple: PropTypes.bool,
};

AddLink.defaultProps = {
  accept: null,
  pattern: null,
  validate: null,
  multiple: false,
};

/** Files of a video (``types/video/uploader.html``). */
export function VideoUploader({ id }) {
  const { record } = useDeposit(id);
  const actions = useDepositActions(id);
  const { isSuperAdmin, videoExtensions } = useConfig();
  // A new video uploads its file once shown
  useStarted(startUploads, id);
  const [hideSubformats, setHideSubformats] = useState(false);
  const [search, setSearch] = useState("");
  const [timesReplacedOpen, setTimesReplacedOpen] = useState(false);
  const files = record._files || [];
  const currentMaster = findMasterFile(record);
  const master = currentMaster || {};
  const published = isPublished(record);
  const posters = findBy(files, "context_type", "poster") || [];
  const subtitles = findBy(files, "context_type", "subtitle") || [];
  const others =
    removeBy(
      removeBy(
        removeBy(files, "context_type", "poster"),
        "context_type",
        "master"
      ),
      "context_type",
      "subtitle"
    ) || [];
  const visibleOthers = angularFilter(others, search);
  const { addFiles } = actions;

  return (
    <>
      <ReplaceMasterDialog
        id={id}
        message={(name) =>
          `Are you sure you want to replace the previously uploaded file with ${name}?`
        }
      />
      {/* Master video and subformats */}
      <div className="cds-panel" style={show(files.length > 0)}>
        <div className="cds-panel-heading">Main &amp; Subformats files</div>
        <table className="cds-table">
          <tbody>
            <tr>
              <th>Filename</th>
              <th>Size</th>
              <th className="text-center">Progress</th>
              <th className="text-center">Actions</th>
            </tr>
            <tr className="active">
              <td title={master.key}>
                {limitTo(master.key, 40)}{" "}
                <span style={show((master.key || "").length > 40)}>...</span>
                {master.tags && master.tags.times_replaced && (
                  <span>
                    <a
                      href="#replaced"
                      onClick={(e) => {
                        e.preventDefault();
                        setTimesReplacedOpen(true);
                      }}
                    >
                      {" "}
                      <span className="cds-badge">
                        {" "}
                        <i className="fa fa-code-fork" />{" "}
                        {master.tags.times_replaced}
                      </span>
                    </a>
                    <DialogModal
                      open={timesReplacedOpen}
                      onClose={() => setTimesReplacedOpen(false)}
                      title="The master video has been replaced"
                    >
                      <p className="text-left">
                        The master video has been replaced{" "}
                        <strong>{master.tags.times_replaced} time(s)</strong>.
                      </p>
                    </DialogModal>
                  </span>
                )}
              </td>
              <td>
                {master.size !== undefined ? (
                  <span>{bytesToHumanReadable(master.size)}</span>
                ) : (
                  <span>Unknown</span>
                )}
              </td>
              <td className="text-center">
                <span
                  style={show(
                    master.percentage < 100 && !master.status_failure
                  )}
                >
                  {" "}
                  %
                </span>
                <span
                  style={show(master.status_pending || master.status_started)}
                >
                  Processing...
                </span>
                <span
                  style={show(master.status_failure)}
                  className="text-danger"
                >
                  Error
                </span>
                <span
                  style={show(
                    (master.status_completed || master.percentage === 100) &&
                      !master.status_failure
                  )}
                  className="text-success"
                >
                  ✓
                </span>
              </td>
              <td style={show(currentMaster)} className="text-center">
                <HowToUpdateDialog />
              </td>
            </tr>
            <tr style={show((master.subformat || []).length > 0)}>
              <td>Subformats ({(master.subformat || []).length})</td>
              <td />
              <td className="text-center" />
              <td className="text-center">
                <a
                  href="#subformats"
                  onClick={(e) => {
                    e.preventDefault();
                    setHideSubformats(!hideSubformats);
                  }}
                >
                  {hideSubformats ? <span>Show</span> : <span>Hide</span>}
                </a>
              </td>
            </tr>
            {(master.subformat || [])
              .filter(
                (f) => f.preset_quality || (f.tags && f.tags.preset_quality)
              )
              .map((f, index) => (
                // eslint-disable-next-line react/no-array-index-key
                <tr
                  key={index}
                  className="sel-file"
                  style={show(!hideSubformats)}
                >
                  <td title={f.preset_quality || f.tags.preset_quality}>
                    {f.preset_quality || f.tags.preset_quality}
                  </td>
                  <td />
                  <td className="text-center">
                    <span style={show(f.status_pending || f.status_started)}>
                      <i className="fa fa-spinner fa-spin" />
                    </span>
                    <span
                      style={show(f.status_failure)}
                      className="text-danger"
                    >
                      Error
                    </span>
                    <span
                      style={show(f.status_completed)}
                      className="text-success"
                    >
                      Done
                    </span>
                    <span
                      style={show(f.status_cancelled)}
                      className="text-muted"
                    >
                      <small>
                        <Tooltip html="Subformat quality skipped because the uploaded video resolution is smaller than this quality">
                          <i className="fa fa-info-circle" />
                        </Tooltip>
                      </small>
                    </span>
                  </td>
                  <td className="text-center">
                    <span style={show(isSuperAdmin)}>
                      <a
                        href="#restart"
                        style={show(f.status_failure || f.status_success)}
                        onClick={(e) => {
                          e.preventDefault();
                          actions.restartTask(f.flow_id, f.task_id);
                        }}
                      >
                        <i className="fa fa-undo" />
                      </a>
                    </span>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
      {/* Thumbnails */}
      <DropZone
        className="cds-panel"
        style={show((master.frame || []).length > 0)}
        clickable={false}
        accept="image/*"
        pattern="image/*"
        multiple
        onFiles={addFiles}
      >
        <div>
          <div className="cds-panel-heading">
            Thumbnails ({(master.frame || []).length + posters.length})
            <span className="pull-right">
              {!published && (
                <AddLink
                  accept="image/*"
                  pattern="image/*"
                  onFiles={addFiles}
                />
              )}
            </span>
          </div>
          <div className="cds-panel-body">
            <div className="cds-deposit-thumbnail-pad">
              {(master.frame || []).concat(posters).map((frame, index) => (
                // eslint-disable-next-line react/no-array-index-key
                <div className="cds-deposit-frame-thumbnail" key={index}>
                  <a
                    href={frame.links && frame.links.self}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <img width="100%" alt="" src={thumbnailPreview(frame)} />
                  </a>
                </div>
              ))}
            </div>
          </div>
          <hr className="my-10" />
          <div className="pa-10 text-muted">
            <TipsBox>
              <li>
                Want to customize the cover of your video? Just upload an image
                named <mark>poster.png</mark> or <mark>poster.jpg</mark>. Need
                to update it later? Simply upload a new image with the same
                name, and the cover will be replaced automatically.
              </li>
            </TipsBox>
          </div>
        </div>
      </DropZone>
      {/* Subtitles */}
      <div className="cds-panel">
        <div className="cds-panel-heading">
          Subtitles
          <span className="pull-right">
            {!published && (
              <AddLink
                accept=".vtt,.srt"
                pattern=".vtt,.srt"
                validate={validateSubtitles}
                onFiles={addFiles}
              />
            )}
          </span>
        </div>
        <SubtitlesBody
          subtitles={subtitles}
          published={published}
          onRemove={actions.removeFile}
          addFiles={addFiles}
        />
      </div>
      {/* Additional files */}
      <div className="cds-panel">
        <div className="cds-panel-heading">Additional files</div>
        <div className="cds-panel-heading" style={show(others.length > 0)}>
          <div className="cds-row">
            <div className="cds-col-sm-6">
              <p style={show(files.length > 0)} className="text-muted" />
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
        </div>
        <table style={show(others.length > 0)} className="cds-table">
          <tbody>
            <tr>
              <th>Filename</th>
              <th>Size</th>
              <th className="text-center">Progress</th>
              <th className="text-center">Actions</th>
            </tr>
            <tr style={show(visibleOthers.length === 0)}>
              <td colSpan="4" className="text-center text-muted">
                {" "}
                No results.
              </td>
            </tr>
            {visibleOthers.map((file, index) => (
              // eslint-disable-next-line react/no-array-index-key
              <tr className="sel-file" key={`${file.key}-${index}`}>
                <FileName file={file} />
                <FileSize file={file} />
                <FileProgress file={file} done="Done" />
                <td className="text-center">
                  {!(file.percentage < 100 || published) && (
                    <RemoveLink onRemove={actions.removeFile} file={file} />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="cds-panel-body">
          {!published && (
            <div className="cds-deposit-box">
              <DropZone
                multiple
                validate={validateAdditionalFiles}
                onFiles={addFiles}
              >
                <div className="pa-10 cds-deposit-box-upload-wrapper text-center">
                  <p className="cds-deposit-box-upload-icon mb-20">
                    <i className="fa fa-3x fa-files-o" aria-hidden="true" />
                  </p>
                  <div className="cds-deposit-box-upload-content">
                    <h4>Upload additional files for this video</h4>
                    <p className="cds-deposit-box-upload-description">
                      Or Drag &amp; Drop files
                    </p>
                  </div>
                </div>
              </DropZone>
            </div>
          )}
        </div>
      </div>
      <hr className="my-20" />
      {/* Replacing Master Video File */}
      {!published && (
        <div className="cds-panel">
          <div className="cds-panel-heading cds-panel-heading-warning">
            <i className="fa fa-exclamation-triangle" aria-hidden="true" />{" "}
            Replace Video File
          </div>
          <div className="cds-panel-body">
            <div className="cds-deposit-box">
              <DropZone
                multiple
                accept={videoExtensions}
                pattern={videoExtensions}
                onFiles={actions.replaceMasterFile}
              >
                <div className="pa-10 cds-deposit-box-upload-wrapper text-center">
                  <p className="cds-deposit-box-upload-icon mb-20">
                    <i
                      className="fa fa-2x fa-video-camera"
                      aria-hidden="true"
                    />
                  </p>
                  <div className="cds-deposit-box-upload-content">
                    <h4>
                      To replace the video file, just upload a video here.
                    </h4>
                    <p className="cds-deposit-box-upload-description">
                      Or Drag &amp; Drop files
                    </p>
                  </div>
                </div>
              </DropZone>
            </div>
          </div>
        </div>
      )}
      {published && (
        <div className="cds-deposit-box text-muted">
          <h5 className="text-muted">
            <strong>Tips and suggestions</strong>
          </h5>
          <ul>
            <li>
              Click the <strong>Edit</strong> button on the top right corner to
              add more files.
            </li>
          </ul>
        </div>
      )}
    </>
  );
}

VideoUploader.propTypes = { id: PropTypes.string.isRequired };

function SubtitlesBody({ subtitles, published, onRemove, addFiles }) {
  if (subtitles.length === 0) {
    if (published) {
      return (
        <div className="cds-panel-body text-center">
          <p className="text-muted text-center f7">No subtitles.</p>
        </div>
      );
    }
    return (
      <DropZone
        className="cds-panel-body text-center"
        multiple
        accept="text/vtt,.vtt,.srt"
        pattern=".vtt,.srt"
        validate={validateSubtitles}
        onFiles={addFiles}
      >
        <p className="text-muted text-center f7">No subtitles.</p>
        <p className="text-muted text-center f8">
          Drag &amp; Drop or <a href="#select">select</a> <mark>.vtt</mark> or{" "}
          <mark>.srt</mark> files.
        </p>
        <hr className="my-10" />
        <div className="text-muted text-left">
          <h5 className="text-muted">
            <strong>Tips and suggestions</strong>
          </h5>
          <ul>
            <li>
              Subtitle filename should have a valid ISO language code. Example:{" "}
              <mark>subtitles_fr.vtt</mark> or <mark>subtitles_fr.srt</mark>{" "}
            </li>
          </ul>
        </div>
      </DropZone>
    );
  }
  return (
    <table className="cds-table">
      <tbody>
        <tr>
          <th>Filename</th>
          <th>Size</th>
          <th className="text-center">Progress</th>
          <th className="text-center">Actions</th>
        </tr>
        {subtitles.map((file, index) => (
          // eslint-disable-next-line react/no-array-index-key
          <tr className="sel-file" key={`${file.key}-${index}`}>
            <FileName file={file} />
            <FileSize file={file} />
            <FileProgress file={file} done="Done" />
            <td className="text-center">
              {!(file.percentage < 100 || published) && (
                <RemoveLink onRemove={onRemove} file={file} />
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

SubtitlesBody.propTypes = {
  subtitles: PropTypes.array.isRequired,
  published: PropTypes.bool.isRequired,
  onRemove: PropTypes.func.isRequired,
  addFiles: PropTypes.func.isRequired,
};
