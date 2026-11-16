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
 * A video of the project (the video panel of deposits.html,
 * types/video/actions.html and types/video/form.html).
 */

import React, { useState } from "react";
import PropTypes from "prop-types";

import { DialogModal } from "@js/cds/components/DialogModal";

import { DEPOSIT_STATUSES, urlBuilder } from "../constants";
import { RestrictionsBox } from "../fields/Access";
import {
  CheckboxField,
  ContributorsField,
  DateField,
  KeywordsField,
  LicensesField,
  RichTextField,
  SelectField,
  TextField,
} from "../fields/Fields";
import {
  CopyrightFieldset,
  RelatedIdentifiersField,
  RelatedLinksField,
  TranslationsField,
} from "../fields/Groups";
import {
  CONTRIBUTOR_ROLES,
  SCHEMA_DESCRIPTIONS,
  VIDEO_EDITOR_TOOLBAR,
  VIDEO_LANGUAGES,
} from "../fields/options";
import { taskRepr } from "../filters";
import {
  useConfig,
  useDeposit,
  useDepositActions,
  useDepositStatus,
  useLoading,
  useProjectRecord,
} from "../state/hooks";
import { findMasterFile, isDraft, isPublished } from "../state/records";
import {
  ErrorAlerts,
  Html,
  ProgressBar,
  Tabs,
  TaskList,
  VideoPreview,
  show,
} from "./common";
import { DepositForm } from "./DepositForm";
import { VideoUploader } from "./Uploaders";

/* Actions (``types/video/actions.html``) */

function VideoActions({ id }) {
  const deposit = useDeposit(id);
  const actions = useDepositActions(id);
  const { showAvcRestrictedFields } = useConfig();
  const project = useProjectRecord();
  const loading = useLoading();
  const [deleteShown, setDeleteShown] = useState(false);
  const [publishShown, setPublishShown] = useState(false);
  const [cannotEditShown, setCannotEditShown] = useState(false);
  const { record, framesReady } = deposit;
  const actionLoading = deposit.pending > 0;
  const success = useDepositStatus(id).status === DEPOSIT_STATUSES.SUCCESS;
  const published = isPublished(record);
  const masterFile = findMasterFile(record) || {};
  const showAssign =
    !record.report_number &&
    showAvcRestrictedFields &&
    project.category &&
    project.type;

  return (
    <div style={show(!deposit.waitingUpload)}>
      <DialogModal
        open={deleteShown}
        onClose={() => setDeleteShown(false)}
        title="Delete video"
      >
        Are you sure you want permanently delete the video?
        <hr className="mt-30 mb-10" />
        <p className="pull-right">
          <button
            type="button"
            className="ui green button"
            onClick={() => {
              actions.remove();
              setDeleteShown(false);
            }}
          >
            Yes
          </button>
          <button
            type="button"
            className="ui red button"
            onClick={() => setDeleteShown(false)}
          >
            No
          </button>
        </p>
      </DialogModal>
      <DialogModal
        open={publishShown}
        onClose={() => setPublishShown(false)}
        title="Publish video"
      >
        The video workflow is still processing.
        <br />
        <br />
        You can publish the video even if not all video subformats have been
        generated yet.
        <br />
        Before publishing the video, make sure that at least on subformats has
        been completed by checking the &quot;Files&quot; tab.
        <br />
        Completed video subformats will be automatically published.
        <br />
        <br />
        Do you want publish the video?
        <br />
        <hr className="mt-30 mb-10" />
        <p className="pull-right">
          <button
            type="button"
            className="ui basic button"
            onClick={() => setPublishShown(false)}
          >
            No
          </button>
          <button
            type="button"
            className="ui green button"
            onClick={() => {
              actions.publishVideo();
              setPublishShown(false);
            }}
          >
            Yes
          </button>
        </p>
      </DialogModal>
      <DialogModal
        open={cannotEditShown}
        onClose={() => setCannotEditShown(false)}
        title="Cannot edit the video"
      >
        You cannot edit the video if the project is published.
        <br />
        Please <strong>edit the project first</strong>, and then edit the video.
        <br />
        <hr className="mt-30 mb-10" />
        <p className="pull-right">
          <button
            type="button"
            className="ui primary button"
            onClick={() => setCannotEditShown(false)}
          >
            Close
          </button>
        </p>
      </DialogModal>
      <div className="text-right">
        {loading && (
          <span>
            <i className="fa fa-spinner fa-spin text-muted fa-fw" />
          </span>
        )}{" "}
        {!(record._deposit.status === "published" || record._deposit.pid) && (
          <>
            <button
              type="button"
              className="ui small basic button"
              disabled={
                (!framesReady || loading) && !(masterFile.size === undefined)
              }
              onClick={() => setDeleteShown(true)}
            >
              <i className="fa fa-trash-o" />
            </button>{" "}
          </>
        )}
        {!published && (
          <>
            <button
              type="button"
              className="ui small green button"
              disabled={!deposit.dirty || loading}
              onClick={() => actions.run("SAVE_PARTIAL")}
            >
              {actionLoading ? "Saving ..." : "Save"}
            </button>{" "}
          </>
        )}
        {success && !published && (
          <>
            <button
              type="button"
              className="ui small primary button"
              disabled={!framesReady || loading || !success}
              onClick={actions.publishVideo}
            >
              {actionLoading ? "Publishing ..." : "Publish"}
            </button>{" "}
          </>
        )}
        {!success && !published && (
          <>
            <button
              type="button"
              className="ui small primary button"
              disabled={!framesReady || loading}
              onClick={() => setPublishShown(true)}
            >
              {actionLoading ? "Publishing ..." : "Publish"}
            </button>{" "}
          </>
        )}
        {!isDraft(record) && (
          <>
            <button
              type="button"
              className="ui small basic button"
              disabled={loading}
              onClick={() =>
                actions.editPublished(() => setCannotEditShown(true))
              }
            >
              {actionLoading ? "Editing ..." : "Edit"}
            </button>{" "}
          </>
        )}
        {showAssign && (
          <a
            className={`ui small orange button${loading ? " disabled" : ""}`}
            href={`/deposit/reportnumbers/assign/${id}`}
          >
            Assign Report Number
          </a>
        )}
      </div>
    </div>
  );
}

VideoActions.propTypes = { id: PropTypes.string.isRequired };

/* Extracted metadata (``Fill metadata suggestion``) */

function ExtractedMetadata({ id }) {
  const { record, metadataToFill } = useDeposit(id);
  const actions = useDepositActions(id);
  const [open, setOpen] = useState(false);
  const toDisplay = metadataToFill ? metadataToFill[1] : {};
  return (
    <div style={show(!isPublished(record))}>
      <div
        style={show(metadataToFill)}
        className="cds-alert cds-alert-warning cds-alert-dismissible cds-deposit-metadata-extraction-alert"
        role="alert"
      >
        <button
          type="button"
          className="cds-close"
          aria-label="Close"
          onClick={actions.dismissExtractedMetadata}
        >
          <span aria-hidden="true">&times;</span>
        </button>
        Extracted metadata can be used to automatically fill part of the form.{" "}
        <button
          type="button"
          className="ui small orange button pull-right"
          onClick={() => setOpen(true)}
        >
          See the extracted metadata
        </button>
      </div>
      <DialogModal
        open={open}
        onClose={() => setOpen(false)}
        title="Are you sure you want to use the following metadata?"
      >
        <ul>
          {Object.entries(toDisplay).map(([key, value]) => (
            <li key={key}>
              <strong>{key}</strong>{" "}
              {typeof value === "string" ? value : JSON.stringify(value)}
            </li>
          ))}
        </ul>
        <hr className="mt-30 mb-10" />
        <p className="pull-right">
          <button
            type="button"
            className="ui basic button"
            onClick={() => {
              actions.fillMetadata(false);
              setOpen(false);
            }}
          >
            No
          </button>
          <button
            type="button"
            className="ui green button"
            onClick={() => {
              actions.fillMetadata(true);
              setOpen(false);
            }}
          >
            Yes
          </button>
        </p>
      </DialogModal>
    </div>
  );
}

ExtractedMetadata.propTypes = { id: PropTypes.string.isRequired };

/* Sidebar of the detail view */

function InheritButton({ id }) {
  const { record } = useDeposit(id);
  const { inheritMetadata } = useDepositActions(id);
  const project = useProjectRecord();
  const [open, setOpen] = useState(false);
  return (
    <div style={show(project.title && !isPublished(record))}>
      <hr className="mt-10 mb-20" />
      <div className="text-center">
        <button
          type="button"
          className="ui small button cds-btn-info"
          onClick={() => setOpen(true)}
        >
          Inherit metadata from project
        </button>
      </div>
      <DialogModal
        open={open}
        onClose={() => setOpen(false)}
        title="Inherit metadata from the project"
      >
        <p className="text-left">
          Please select if you would like to replace all metadata of this video
          or inherit only the missing metadata from the project.
        </p>
        <hr className="mt-30 mb-10" />
        <p className="pull-right">
          <button
            type="button"
            className="ui basic button"
            onClick={() => {
              inheritMetadata(false);
              setOpen(false);
            }}
          >
            Only the missing fields
          </button>
          <button
            type="button"
            className="ui basic button"
            onClick={() => {
              inheritMetadata(true);
              setOpen(false);
            }}
          >
            Replace all metadata
          </button>
        </p>
      </DialogModal>
    </div>
  );
}

InheritButton.propTypes = { id: PropTypes.string.isRequired };

function VideoSidebar({ id, onTranscodeInfo }) {
  const { record } = useDeposit(id);
  const { showAvcRestrictedFields } = useConfig();
  const master = useProjectRecord();
  const published = isPublished(record);
  const recordUrl = urlBuilder.record({ recid: record.recid });
  return (
    <div className="cds-col-sm-3">
      <VideoPreview id={id} />
      <div>
        {master.category && (
          <div className="text-muted mt-10">
            <div className="cds-row">
              <div className="cds-col-md-6">
                <p className="mb-0">Category</p>
                {master.category && (
                  <p>
                    <span className="ui label cds-label cds-label-default">
                      {master.category}
                    </span>
                  </p>
                )}
              </div>
              <div className="cds-col-md-6">
                <p className="mb-0">Type</p>
                {master.type && (
                  <p>
                    <span className="ui label cds-label cds-label-warning">
                      {master.type}
                    </span>
                  </p>
                )}
              </div>
            </div>
            <hr className="my-10" />
          </div>
        )}
        {!master.category && (
          <div className="text-muted mt-10">
            <i className="fa fa-info-circle" /> For publishing the video{" "}
            {showAvcRestrictedFields && (
              <span>, or assigning a report number, </span>
            )}{" "}
            please select category and type from the{" "}
            <a
              href={`#${master._deposit.id}`}
              onClick={(e) => {
                e.preventDefault();
                const target = document.getElementById(master._deposit.id);
                if (target) {
                  target.scrollIntoView({ behavior: "smooth" });
                }
              }}
            >
              Project
            </a>
            .
            <hr className="my-10" />
          </div>
        )}
        <p className="text-muted mb-0">
          <strong>Video status:</strong>
        </p>
        <div style={show(published)}>
          <p className="text-muted mb-0">
            <span className="ui label cds-label cds-label-primary">
              Published
            </span>
          </p>
          <hr className="my-10" />
          <p className="mt-10">
            <i className="fa text-muted fa-link" />{" "}
            <a href={recordUrl}>Visit video page</a>
          </p>
        </div>
        <div style={show(!published)} className="text-muted">
          <p>
            The video is <strong>not</strong> published.
          </p>
          <ul className="list-unstyled text-left my">
            <TaskList
              state={record._cds && record._cds.state}
              small
              onTranscodeInfo={onTranscodeInfo}
            />
          </ul>
        </div>
        <InheritButton id={id} />
      </div>
    </div>
  );
}

VideoSidebar.propTypes = {
  id: PropTypes.string.isRequired,
  onTranscodeInfo: PropTypes.func.isRequired,
};

/* Tabs */

function BasicInfo({ id }) {
  const { showAvcRestrictedFields } = useConfig();
  return (
    <>
      <form className="form" onSubmit={(e) => e.preventDefault()}>
        <TextField name="title.title" label="Title" required />
        <RichTextField
          name="description"
          label="Description"
          required
          description="Required."
          toolbar={VIDEO_EDITOR_TOOLBAR}
        />
        <KeywordsField
          name="keywords"
          label="Keywords"
          placeholder="Keywords"
          description="Search or add keywords as a comma separated list e.g. keyword1, keyword2 etc."
        />
        <SelectField
          name="language"
          label="Language"
          required
          options={VIDEO_LANGUAGES}
          description={SCHEMA_DESCRIPTIONS.language}
        />
        <DateField
          name="date"
          label="Date"
          required
          description="Required. Format: YYYY-MM-DD. In case your upload was already published elsewhere, please use the date of first publication."
        />
        <ContributorsField roles={CONTRIBUTOR_ROLES} />
        {showAvcRestrictedFields === true && (
          <CheckboxField
            name="featured"
            label="Feature this video on the home page"
          />
        )}
        <CheckboxField name="vr" label="This video is 360" />
      </form>
      <hr className="my-15" />
      <RestrictionsBox id={id} />
    </>
  );
}

BasicInfo.propTypes = { id: PropTypes.string.isRequired };

function RestartTasks({ id }) {
  const { record, tasksByName } = useDeposit(id);
  const actions = useDepositActions(id);
  return (
    <div className="cds-panel">
      <div className="cds-panel-heading">
        Restart tasks{" "}
        <a
          href="#restart"
          className="cds-btn-link cds-btn-xs pull-right"
          onClick={(e) => {
            e.preventDefault();
            actions.restartFlow();
          }}
        >
          <i className="fa fa-refresh" aria-hidden="true" /> Restart All
        </a>
      </div>
      <div className="cds-panel-body">
        {Object.entries(tasksByName || {}).map(([name, data]) => {
          const first = data[0] || {};
          const payload = (first.info && first.info.payload) || {};
          const running = (status) =>
            status === "PENDING" || status === "STARTED";
          if (name === "file_transcode") {
            return (
              <ul className="cds-list-group" key={name}>
                <li className="cds-list-group-item">
                  <p>
                    <strong>{name}</strong>
                  </p>
                  <div className="mb-10 text-center">
                    <i className="fa fa-external-link" aria-hidden="true" />{" "}
                    <a
                      href={`/admin/flowmetadata/?search=${payload.flow_id}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      See Flow
                    </a>
                    &nbsp;&nbsp;{" "}
                    <i className="fa fa-external-link" aria-hidden="true" />{" "}
                    <a
                      href={`/admin/flowtaskmetadata/?search=${payload.flow_id}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      See Tasks
                    </a>
                  </div>
                  {data.map((task, index) => {
                    const taskPayload = (task.info && task.info.payload) || {};
                    const blocked =
                      running(task.status) || task.status === "CANCELLED";
                    return (
                      // eslint-disable-next-line react/no-array-index-key
                      <ul className="cds-list-group" key={index}>
                        <li className="cds-list-group-item">
                          {taskPayload.preset_quality}{" "}
                          <span className="ui label cds-label cds-label-default">
                            {task.status}
                          </span>
                          <a
                            href="#restart"
                            className="pull-right"
                            style={
                              blocked ? { pointerEvents: "none" } : undefined
                            }
                            onClick={(e) => {
                              e.preventDefault();
                              if (!(isDraft(record) || blocked)) {
                                actions.restartTask(
                                  taskPayload.flow_id,
                                  taskPayload.task_id
                                );
                              }
                            }}
                          >
                            <i
                              style={show(
                                task.status === "SUCCESS" ||
                                  task.status === "FAILURE"
                              )}
                              className={`fa fa-refresh ${task.status}`}
                              aria-hidden="true"
                            />
                            <i
                              style={show(running(task.status))}
                              className="fa fa-spinner fa-spin"
                            />
                          </a>
                        </li>
                      </ul>
                    );
                  })}
                </li>
              </ul>
            );
          }
          return (
            <ul className="cds-list-group" key={name}>
              <li className="cds-list-group-item">
                <strong>{name}</strong>{" "}
                <span className="ui label cds-label cds-label-default">
                  {first.status}
                </span>
                <a
                  href="#restart"
                  className="pull-right"
                  style={
                    running(first.status)
                      ? { pointerEvents: "none" }
                      : undefined
                  }
                  onClick={(e) => {
                    e.preventDefault();
                    if (first.status !== "PENDING") {
                      actions.restartTask(payload.flow_id, payload.task_id);
                    }
                  }}
                >
                  <i
                    style={show(
                      first.status === "SUCCESS" || first.status === "FAILURE"
                    )}
                    className={`fa fa-refresh ${first.status}`}
                    aria-hidden="true"
                  />
                  <i
                    style={show(running(first.status))}
                    className="fa fa-spinner fa-spin"
                  />
                </a>
              </li>
            </ul>
          );
        })}
      </div>
    </div>
  );
}

RestartTasks.propTypes = { id: PropTypes.string.isRequired };

function AdminTab({ id }) {
  const { record } = useDeposit(id);
  const [showMetadata, setShowMetadata] = useState(false);
  return (
    <>
      <div className="mb-10 text-center">
        <i className="fa fa-external-link" aria-hidden="true" />{" "}
        <a href={`/api/deposits/video/${id}`} target="_blank" rel="noreferrer">
          See JSON
        </a>
      </div>
      <RestartTasks id={id} />
      <div className="cds-panel">
        <div className="cds-panel-heading">Record metadata</div>
        <div className="cds-panel-body">
          <div className="text-center">
            <a
              href="#metadata"
              onClick={(e) => {
                e.preventDefault();
                setShowMetadata(!showMetadata);
              }}
            >
              {" "}
              {showMetadata ? "Hide" : "Show"} metadata
            </a>
          </div>
          <span style={show(showMetadata)}>
            {showMetadata && <pre>{JSON.stringify(record, null, 2)}</pre>}
          </span>
        </div>
      </div>
    </>
  );
}

AdminTab.propTypes = { id: PropTypes.string.isRequired };

function VideoTabs({ id }) {
  const { record } = useDeposit(id);
  const { isSuperAdmin } = useConfig();
  const [active, setActive] = useState("metadata");
  const pane = (key) => ({ display: active === key ? undefined : "none" });
  return (
    <div className="cds-col-sm-9">
      <Tabs
        active={active}
        onChange={setActive}
        tabs={[
          { key: "metadata", title: "Basic Info" },
          { key: "files", title: "Files" },
          { key: "licenses", title: "Licences" },
          { key: "translations", title: "Translations" },
          { key: "related_links", title: "Related information" },
          {
            key: "admin",
            hidden: !isSuperAdmin,
            title: (
              <>
                <i className="fa fa-bug" aria-hidden="true" /> Admin
              </>
            ),
          },
        ]}
      />
      <div className="tab-content cds-tab-content pa-20">
        <div style={pane("metadata")} role="tabpanel" className="tab-pane">
          <BasicInfo id={id} />
        </div>
        <div style={pane("files")} role="tabpanel" className="tab-pane">
          <VideoUploader id={id} />
        </div>
        <div style={pane("licenses")} role="tabpanel" className="tab-pane">
          <form className="form" onSubmit={(e) => e.preventDefault()}>
            <LicensesField />
            <CopyrightFieldset />
          </form>
        </div>
        <div style={pane("translations")} role="tabpanel" className="tab-pane">
          <form className="form" onSubmit={(e) => e.preventDefault()}>
            <TranslationsField />
          </form>
          {!isPublished(record) && (
            <div className="cds-deposit-box">
              <div className="text-muted">
                <h5 className="text-muted">
                  <strong>Tips and suggestions</strong>
                </h5>
                <ul>
                  <li>
                    You can upload subtitle files in the <strong>Files</strong>{" "}
                    tab.
                  </li>
                </ul>
              </div>
            </div>
          )}
        </div>
        <div style={pane("related_links")} role="tabpanel" className="tab-pane">
          <form className="form" onSubmit={(e) => e.preventDefault()}>
            <RelatedLinksField />
            <RelatedIdentifiersField />
          </form>
        </div>
        <div style={pane("admin")} role="tabpanel" className="tab-pane">
          <AdminTab id={id} />
        </div>
      </div>
    </div>
  );
}

VideoTabs.propTypes = { id: PropTypes.string.isRequired };

/* The video form (``types/video/form.html``) */

function VideoForm({ id, onTranscodeInfo }) {
  const { record, showAll, waitingUpload } = useDeposit(id);
  const { changeShowAll } = useDepositActions(id);
  const { status, startedTask } = useDepositStatus(id);
  const master = useProjectRecord();
  const published = isPublished(record);
  const recordUrl = urlBuilder.record({ recid: record.recid });
  const firstFile = (record._files || [])[0] || {};
  return (
    <>
      <ErrorAlerts id={id} />
      <ExtractedMetadata id={id} />
      <div className="cds-row" style={show(!waitingUpload)}>
        {/* Brief view */}
        <div style={show(published && !showAll)} className="cds-col-sm-12">
          <div className="cds-row">
            <div className="cds-col-sm-3">
              <VideoPreview id={id} />
            </div>
            <div className="cds-col-sm-9">
              <ul className="cds-list-inline">
                <li>
                  <span className="ui label cds-label cds-label-default">
                    {master.category}
                  </span>
                </li>{" "}
                <li>
                  <span className="ui label cds-label cds-label-warning">
                    {master.type}
                  </span>
                </li>{" "}
                <li>
                  <span className="ui label cds-label cds-label-primary">
                    Published
                  </span>
                </li>
              </ul>
              <hr className="my-15" />
              <h4 className="mb-5 mt-0">
                <a href={recordUrl}>
                  {(record.title && record.title.title) || "No video title"}
                </a>
              </h4>
              <Html html={record.description || "No description"} />
            </div>
          </div>
        </div>
        {/* Detail view */}
        <div
          style={show(!published || (published && showAll))}
          className="cds-col-sm-12"
        >
          <div className="cds-row">
            <div className="cds-col-sm-12">
              <div style={show(status === DEPOSIT_STATUSES.PENDING)}>
                <ProgressBar striped active>
                  Loading ...
                </ProgressBar>
              </div>
              <div
                style={show(status === DEPOSIT_STATUSES.STARTED)}
                className="cds-row"
              >
                <ProgressBar striped active>
                  {taskRepr(startedTask)}
                </ProgressBar>
              </div>
              <div
                style={show(
                  status === DEPOSIT_STATUSES.SUCCESS &&
                    !published &&
                    !record.recid
                )}
                className="cds-row"
              >
                <ProgressBar success>
                  <strong>Tasks successfully completed!</strong>
                </ProgressBar>
              </div>
            </div>
            <VideoSidebar id={id} onTranscodeInfo={onTranscodeInfo} />
            <VideoTabs id={id} />
          </div>
        </div>
        <div style={show(published)} className="cds-row">
          <div className="cds-col-sm-12 text-center">
            <div className="px-20">
              <hr className="mb-15" />
              <button
                type="button"
                className="ui small basic button"
                onClick={() => changeShowAll(showAll)}
              >
                {showAll ? "Hide details" : "Show details"}
              </button>
            </div>
          </div>
        </div>
      </div>
      {/* Waiting for the upload */}
      <div className="cds-row" style={show(waitingUpload)}>
        <div className="cds-col-md-12">
          <div className="cds-progress">
            <div
              style={{
                ...show(firstFile.percentage),
                width: `${firstFile.percentage || 0}%`,
              }}
              className="cds-progress-bar cds-progress-bar-primary"
              role="progressbar"
            >
              <span className="sr-only">
                {firstFile.percentage || 0}% Complete
              </span>
            </div>
            <div
              style={{ ...show(!firstFile.percentage), width: "100%" }}
              className="cds-progress-bar cds-progress-bar-primary cds-progress-bar-striped active"
              role="progressbar"
            >
              <span className="sr-only">Loading ...</span>
              Loading ...
            </div>
          </div>
          <p
            style={show(firstFile.percentage)}
            className="text-muted text-center f5"
          >
            {firstFile.percentage || 0}%
          </p>
        </div>
      </div>
    </>
  );
}

VideoForm.propTypes = {
  id: PropTypes.string.isRequired,
  onTranscodeInfo: PropTypes.func.isRequired,
};

/* The video panel (``deposits.html``) */

export function VideoPanel({ id, index, onTranscodeInfo }) {
  const reportNumber = useDeposit(id).record.report_number;
  const { maxNumberOfVideos } = useConfig();
  return (
    <div id={id}>
      <div id={`video_${id}`} className="cds-deposit-panel cds-panel">
        <div className="cds-panel-heading text-muted px-20 py-10 cds-sticky-heading">
          <span className="text-muted">
            <i className="fa fa-video-camera" /> Video #{index + 1} (of{" "}
            {maxNumberOfVideos}){" "}
            {reportNumber && (
              <span className="ui label cds-label cds-label-primary ml-10">
                {" "}
                {reportNumber[0]}{" "}
              </span>
            )}
          </span>
          <span className="pull-right">
            <VideoActions id={id} />
          </span>
        </div>
        <div className="cds-panel-body">
          <DepositForm id={id}>
            <VideoForm id={id} onTranscodeInfo={onTranscodeInfo} />
          </DepositForm>
        </div>
      </div>
    </div>
  );
}

VideoPanel.propTypes = {
  id: PropTypes.string.isRequired,
  index: PropTypes.number.isRequired,
  onTranscodeInfo: PropTypes.func.isRequired,
};
