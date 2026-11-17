/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Tabs of the video form. */

import React, { useState } from "react";
import PropTypes from "prop-types";
import { Icon, Message } from "semantic-ui-react";

import { prevent } from "@js/cds/shared/dom";

import { RestrictionsBox } from "../fields/Access";
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
import { useConfig, useDeposit } from "../state/hooks";
import { isPublished } from "../state/records";
import { VideoUploader } from "../uploads/VideoUploader";
import { TipsBox } from "../components/TipsBox";
import { Tabs } from "../components/Tabs";
import { RestartTasks } from "./RestartTasks";
import {
  CheckboxField,
  DateField,
  SelectField,
  TextField,
} from "../fields/BasicFields";
import { RichTextField } from "../fields/RichTextField";
import { KeywordsField } from "../fields/KeywordsField";
import { ContributorsField } from "../fields/ContributorsField";
import { LicensesField } from "../fields/LicensesField";

/* Tabs */

/* Under the video description: the chapters are lines starting with a time */
const CHAPTERS_NOTE = (
  <Message info size="tiny">
    <Icon name="info circle" />
    <strong>Chapters:</strong> start a line with a time and a title, e.g.{" "}
    <code>0:00 Introduction</code>. A time inside a sentence is not a chapter.
  </Message>
);

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
        {CHAPTERS_NOTE}
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
              onClick={prevent(() => setShowMetadata(!showMetadata))}
            >
              {" "}
              {showMetadata ? "Hide" : "Show"} metadata
            </a>
          </div>
          {showMetadata && (
            <span>
              {showMetadata && <pre>{JSON.stringify(record, null, 2)}</pre>}
            </span>
          )}
        </div>
      </div>
    </>
  );
}

AdminTab.propTypes = { id: PropTypes.string.isRequired };

export function VideoTabs({ id }) {
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
              <TipsBox>
                <li>
                  You can upload subtitle files in the <strong>Files</strong>{" "}
                  tab.
                </li>
              </TipsBox>
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
