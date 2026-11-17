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
 * Files of a video: the uploaded video and its processing, subtitles and
 * other files.
 */

import React, { useState } from "react";
import PropTypes from "prop-types";

import { DialogModal } from "@js/cds/shared/components/DialogModal";
import { Tooltip } from "@js/cds/shared/components/Popups";
import { filterByText, findBy } from "@js/cds/shared/utils/collections";
import { prevent, show } from "@js/cds/shared/dom";

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
import { TipsBox } from "../components/TipsBox";
import {
  FileName,
  FILES_HEADER,
  SearchRow,
  UploadBox,
  FileSize,
  FileProgress,
  RemoveLink,
} from "./FileTable";
import { HowToUpdateDialog, ReplaceMasterDialog } from "./UploadDialogs";

function AddLink({
  onFiles,
  accept = null,
  pattern = null,
  validate = null,
  multiple = false,
}) {
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

/** Files of a video. */
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
  const others = files.filter(
    (file) => !["poster", "master", "subtitle"].includes(file.context_type)
  );
  const visibleOthers = filterByText(others, search);
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
      {files.length > 0 && (
        <div className="cds-panel">
          <div className="cds-panel-heading">Main &amp; Subformats files</div>
          <table className="cds-table">
            <tbody>
              {FILES_HEADER}
              <tr className="active">
                <FileName file={master}>
                  {master.tags && master.tags.times_replaced && (
                    <span>
                      <a
                        href="#replaced"
                        onClick={prevent(() => setTimesReplacedOpen(true))}
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
                </FileName>
                <FileSize file={master} />
                <td className="text-center">
                  {master.percentage < 100 && !master.status_failure && (
                    <span> %</span>
                  )}
                  {(master.status_pending || master.status_started) && (
                    <span>Processing...</span>
                  )}
                  {master.status_failure && (
                    <span className="text-danger">Error</span>
                  )}
                  {(master.status_completed || master.percentage === 100) &&
                    !master.status_failure && (
                      <span className="text-success">✓</span>
                    )}
                </td>
                {/* Hidden, not removed: CSS pads the last cell of the row */}
                <td style={show(currentMaster)} className="text-center">
                  <HowToUpdateDialog />
                </td>
              </tr>
              {(master.subformat || []).length > 0 && (
                <tr>
                  <td>Subformats ({(master.subformat || []).length})</td>
                  <td />
                  <td className="text-center" />
                  <td className="text-center">
                    <a
                      href="#subformats"
                      onClick={prevent(() =>
                        setHideSubformats(!hideSubformats)
                      )}
                    >
                      {hideSubformats ? <span>Show</span> : <span>Hide</span>}
                    </a>
                  </td>
                </tr>
              )}
              {(master.subformat || [])
                .filter(
                  (f) => f.preset_quality || (f.tags && f.tags.preset_quality)
                )
                .map((f, index) =>
                  // eslint-disable-next-line react/no-array-index-key
                  !hideSubformats ? (
                    <tr key={index} className="sel-file">
                      <td title={f.preset_quality || f.tags.preset_quality}>
                        {f.preset_quality || f.tags.preset_quality}
                      </td>
                      <td />
                      <td className="text-center">
                        {(f.status_pending || f.status_started) && (
                          <span>
                            <i className="fa fa-spinner fa-spin" />
                          </span>
                        )}
                        {f.status_failure && (
                          <span className="text-danger">Error</span>
                        )}
                        {f.status_completed && (
                          <span className="text-success">Done</span>
                        )}
                        {f.status_cancelled && (
                          <span className="text-muted">
                            <small>
                              <Tooltip html="Subformat quality skipped because the uploaded video resolution is smaller than this quality">
                                <i className="fa fa-info-circle" />
                              </Tooltip>
                            </small>
                          </span>
                        )}
                      </td>
                      <td className="text-center">
                        {isSuperAdmin && (
                          <span>
                            {(f.status_failure || f.status_success) && (
                              <a
                                href="#restart"
                                onClick={prevent(() =>
                                  actions.restartTask(f.flow_id, f.task_id)
                                )}
                              >
                                <i className="fa fa-undo" />
                              </a>
                            )}
                          </span>
                        )}
                      </td>
                    </tr>
                  ) : null
                )}
            </tbody>
          </table>
        </div>
      )}
      {/* Thumbnails */}
      {(master.frame || []).length > 0 && (
        <DropZone
          className="cds-panel"
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
                  Want to customize the cover of your video? Just upload an
                  image named <mark>poster.png</mark> or <mark>poster.jpg</mark>
                  . Need to update it later? Simply upload a new image with the
                  same name, and the cover will be replaced automatically.
                </li>
              </TipsBox>
            </div>
          </div>
        </DropZone>
      )}
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
        {others.length > 0 && (
          <div className="cds-panel-heading">
            <SearchRow files={files} search={search} setSearch={setSearch} />
          </div>
        )}
        {others.length > 0 && (
          <table className="cds-table">
            <tbody>
              {FILES_HEADER}
              {/* Hidden, not removed: CSS styles the first row of the table */}
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
        )}
        <div className="cds-panel-body">
          {!published && (
            <div className="cds-deposit-box">
              <DropZone
                multiple
                validate={validateAdditionalFiles}
                onFiles={addFiles}
              >
                <UploadBox
                  icon="fa-3x fa-files-o"
                  title="Upload additional files for this video"
                />
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
                <UploadBox
                  icon="fa-2x fa-video-camera"
                  title="To replace the video file, just upload a video here."
                />
              </DropZone>
            </div>
          </div>
        </div>
      )}
      {published && (
        <TipsBox className="cds-deposit-box text-muted">
          <li>
            Click the <strong>Edit</strong> button on the top right corner to
            add more files.
          </li>
        </TipsBox>
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
        <TipsBox className="text-muted text-left">
          <li>
            Subtitle filename should have a valid ISO language code. Example:{" "}
            <mark>subtitles_fr.vtt</mark> or <mark>subtitles_fr.srt</mark>{" "}
          </li>
        </TipsBox>
      </DropZone>
    );
  }
  return (
    <table className="cds-table">
      <tbody>
        {FILES_HEADER}
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
