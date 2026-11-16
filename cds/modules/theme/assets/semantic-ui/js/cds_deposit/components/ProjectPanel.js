/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* The project (types/project/form.html and types/project/actions.html). */

import React, { useState } from "react";
import PropTypes from "prop-types";

import { EditorsField, RestrictionsBox } from "../fields/Access";
import { CategoryField, TypeField } from "../fields/CategoryType";
import {
  CKEditorField,
  ContributorsField,
  KeywordsField,
  LicensesField,
  TextField,
} from "../fields/Fields";
import {
  CONTRIBUTOR_ROLES,
  PROJECT_CKEDITOR_CONFIG,
  SCHEMA_DESCRIPTIONS,
} from "../fields/options";
import { TranslationsField } from "../fields/Groups";
import {
  useAnyVideoPublished,
  useConfig,
  useDeposit,
  useDepositActions,
  useLoading,
} from "../state/hooks";
import { isPublished } from "../state/records";
import { isInvalid } from "../state/selectors";
import { ErrorAlerts, Html, InfoDialog, Tabs } from "./common";
import { urlBuilder } from "../constants";
import { DepositForm } from "./DepositForm";
import { ProjectUploader } from "./Uploaders";

function ProjectActions({ id }) {
  const deposit = useDeposit(id);
  const actions = useDepositActions(id);
  const loading = useLoading();
  const status = deposit.record._deposit.status;
  const actionLoading = deposit.pending > 0;
  return (
    <>
      {status !== "published" && (
        <button
          type="button"
          className="ui small green button"
          disabled={!deposit.dirty || loading}
          onClick={actions.saveAll}
        >
          {actionLoading ? "Saving ..." : "Save Project and Videos"}
        </button>
      )}{" "}
      {status !== "published" && (
        <button
          type="button"
          className="ui small primary button"
          disabled={isInvalid(deposit) || loading}
          onClick={() => actions.run("PUBLISH")}
        >
          {actionLoading ? "Publishing ..." : "Publish Project and Videos"}
        </button>
      )}{" "}
      {status !== "draft" && (
        <button
          type="button"
          className="ui small basic button"
          disabled={loading}
          onClick={() => actions.run(["EDIT", "SAVE_PARTIAL"])}
        >
          {actionLoading ? "Editing ..." : "Edit Project"}
        </button>
      )}
    </>
  );
}

ProjectActions.propTypes = { id: PropTypes.string.isRequired };

function ShowDetailsButton({ label, onClick }) {
  return (
    <button type="button" className="ui small basic button" onClick={onClick}>
      {label}
    </button>
  );
}

ShowDetailsButton.propTypes = {
  label: PropTypes.string.isRequired,
  onClick: PropTypes.func.isRequired,
};

function ProjectFields({ id }) {
  const { showAvcRestrictedFields } = useConfig();
  return (
    <div className="cds-row">
      <div className="cds-col-sm-6">
        <TextField name="title.title" label="Title" required />
        <div className="form-ckeditor">
          <CKEditorField
            name="description"
            label="Description"
            required
            config={PROJECT_CKEDITOR_CONFIG}
          />
        </div>
        <KeywordsField
          name="keywords"
          label="Keywords"
          placeholder="Keywords"
          description="Search or add keywords as a comma separated list e.g. keyword1, keyword2 etc."
        />
        {showAvcRestrictedFields === true && (
          <TextField
            name="_eos_library_path"
            label="EOS library path"
            description={SCHEMA_DESCRIPTIONS._eos_library_path}
          />
        )}
      </div>
      <div className="cds-col-sm-6">
        <CategoryField withDescription />
        <TypeField withDescription />
        <ContributorsField roles={CONTRIBUTOR_ROLES} />
      </div>
      <div className="cds-col-sm-12">
        <hr className="my-15" />
        <RestrictionsBox id={id} project />
      </div>
    </div>
  );
}

ProjectFields.propTypes = { id: PropTypes.string.isRequired };

export function ProjectPanel({ id }) {
  const { record, pending } = useDeposit(id);
  const actions = useDepositActions(id);
  const config = useConfig();
  const anyVideoPublished = useAnyVideoPublished();
  const [collapsed, setCollapsed] = useState(true);
  const [active, setActive] = useState("metadata");
  const published = isPublished(record);
  const actionLoading = pending > 0;

  return (
    <DepositForm id={id}>
      <div className="cds-panel cds-deposit-panel cds-deposit-panel-project">
        <div className="cds-panel-heading px-20 py-10">
          <span className=" text-muted">
            <i className="fa fa-list-ul" /> Project
          </span>
          <div className="pull-right">
            <InfoDialog
              title="What is a project?"
              trigger={(open) => (
                <button
                  type="button"
                  className="ui small basic button"
                  onClick={open}
                >
                  <i className="fa fa-info" />
                </button>
              )}
            >
              <div className="text-left">
                <p>
                  A project is a set of metadata common to a collection of
                  videos.
                </p>
                <p>
                  You can define category, type, license and access restriction
                  on the project and they will be applied to each video of the
                  project.
                </p>
              </div>
            </InfoDialog>{" "}
            <ProjectActions id={id} />
          </div>
        </div>
        <div className="cds-panel-body">
          <ErrorAlerts id={id} />
          {/* Collapsed */}
          <div style={{ display: collapsed ? undefined : "none" }}>
            <div style={{ display: published ? undefined : "none" }}>
              <ul className="cds-list-inline">
                <li>
                  <span className="ui label cds-label cds-label-default">
                    {record.category}
                  </span>
                </li>{" "}
                <li>
                  <span className="ui label cds-label cds-label-warning">
                    {record.type}
                  </span>
                </li>{" "}
                <li>
                  <span className="ui label cds-label cds-label-primary">
                    Published
                  </span>
                </li>
              </ul>
              <hr className="my-15" />
              <h3 className="mb-5 mt-0">
                <a href={urlBuilder.record({ recid: record.recid })}>
                  {(record.title && record.title.title) || "No video title"}
                </a>
              </h3>
              <Html
                className="f6"
                html={record.description || "No description"}
              />
            </div>
            {!published && (
              <div>
                <div className="cds-row">
                  <div className="cds-col-sm-6">
                    <CategoryField />
                  </div>
                  <div className="cds-col-sm-6">
                    <TypeField />
                  </div>
                </div>
                <div className="cds-row">
                  <div className="cds-col-sm-12 text-center text-muted">
                    {!anyVideoPublished && (
                      <span>
                        Select category and type, they will be applied to the
                        project and all videos.
                        <br />
                        <br />
                        Each project can contain{" "}
                        <strong>maximum {config.maxNumberOfVideos}</strong>{" "}
                        videos.
                      </span>
                    )}
                    {anyVideoPublished && (
                      <span>
                        Category and type can be changed only if no video has
                        been published yet.
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )}
            <div className="cds-row">
              <div className="cds-col-sm-12 text-center">
                <hr className="mb-15" />
                <ShowDetailsButton
                  label="Show details"
                  onClick={() => setCollapsed(false)}
                />
              </div>
            </div>
          </div>
          {/* Expanded */}
          {
            <div
              className="cds-row"
              style={{ display: collapsed ? "none" : undefined }}
            >
              <div className="cds-col-sm-12">
                <Tabs
                  active={active}
                  onChange={setActive}
                  tabs={[
                    { key: "metadata", title: "Basic Info" },
                    { key: "files", title: "Files" },
                    { key: "licenses", title: "Licences" },
                    { key: "translations", title: "Translations" },
                    { key: "access", title: "Project editors" },
                    {
                      key: "admin",
                      hidden: !config.isSuperAdmin,
                      title: (
                        <>
                          <i className="fa fa-bug" aria-hidden="true" /> Admin
                        </>
                      ),
                    },
                  ]}
                />
                <div className="tab-content cds-tab-content pt-20 px-20">
                  <div
                    style={{
                      display: active === "metadata" ? undefined : "none",
                    }}
                  >
                    <ProjectFields id={id} />
                  </div>
                  <div
                    style={{ display: active === "files" ? undefined : "none" }}
                  >
                    <ProjectUploader id={id} />
                  </div>
                  <div
                    style={{
                      display: active === "licenses" ? undefined : "none",
                    }}
                  >
                    <div className="cds-row">
                      <div className="cds-col-sm-12">
                        <LicensesField />
                      </div>
                    </div>
                  </div>
                  <div
                    style={{
                      display: active === "translations" ? undefined : "none",
                    }}
                  >
                    <div className="cds-row">
                      <div className="cds-col-sm-12">
                        <TranslationsField project />
                      </div>
                    </div>
                  </div>
                  <div
                    style={{
                      display: active === "access" ? undefined : "none",
                    }}
                  >
                    <EditorsField id={id} />
                  </div>
                  <div
                    style={{ display: active === "admin" ? undefined : "none" }}
                  >
                    <div className="mb-10 text-center">
                      <i className="fa fa-external-link" aria-hidden="true" />{" "}
                      <a
                        href={config.projectLinks && config.projectLinks.self}
                        target="_blank"
                        rel="noreferrer"
                      >
                        See JSON
                      </a>
                    </div>
                    <div className="cds-panel cds-panel-danger">
                      <div className="cds-panel-heading">Danger Zone</div>
                      <div className="cds-panel-body">
                        <button
                          type="button"
                          className="ui large red button"
                          disabled={actionLoading}
                          onClick={actions.remove}
                        >
                          {actionLoading ? "Deleting ..." : "Delete Project"}
                        </button>
                      </div>
                    </div>
                  </div>
                  <div className="cds-col-sm-12 pa-5">
                    <hr className="mb-15" />
                    <div className="text-center">
                      <ShowDetailsButton
                        label="Hide details"
                        onClick={() => setCollapsed(true)}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          }
        </div>
      </div>
    </DepositForm>
  );
}

ProjectPanel.propTypes = { id: PropTypes.string.isRequired };
