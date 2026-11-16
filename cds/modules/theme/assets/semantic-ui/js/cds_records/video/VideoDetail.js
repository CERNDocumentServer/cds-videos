/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* static/templates/cds_records/video/detail.html */

import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import DOMPurify from "dompurify";
import { Placeholder } from "semantic-ui-react";

import { DialogModal } from "@js/cds/components/DialogModal";
import { Tooltip } from "@js/cds/components/Popups";
import {
  absoluteURL,
  angularFilterBy,
  findMaster,
  formatDate,
  formatRelationResourceType,
  get,
  getVttSubtitles,
  groupBy,
  isEmpty,
  isoToLanguage,
  isPublic,
  previewIframeSrc,
  replace,
} from "@js/cds/utils";

import { DoiBadge, Html, Keywords, ReportNumberBadge } from "../common";
import {
  buildChapterFrames,
  cleanHtmlFromTitle,
  filterTranscript,
  parseVttFromUrl,
  prepareDescriptions,
  prepareRelatedIdentifiers,
  scrollToElement,
  seekTo,
} from "../helpers";
import { Downloads } from "./Downloads";
import { InThisVideo, usePlayerHighlights } from "./InThisVideo";
import { RelatedEventSection } from "./RelatedEventSection";
import { Share } from "./Share";
import { TechnicalMetadata } from "./TechnicalMetadata";

const UNKNOWN_LICENSE_TEXT =
  "This resource is copyrighted as non-CERN and unfortunately we don't have enough information about its licence. None of CERN's terms of use will apply. Please contact the copyright holder directly for more information.";

/** Trusted HTML of the record, sanitized. */
function sanitize(html) {
  return DOMPurify.sanitize(html || "", { ADD_ATTR: ["target"] });
}

function UnknownLicense({ label, title }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <a
        href="#licence"
        onClick={(e) => {
          e.preventDefault();
          setOpen(true);
        }}
      >
        {label}
      </a>
      <DialogModal open={open} onClose={() => setOpen(false)} title={title}>
        <div>
          <p>{UNKNOWN_LICENSE_TEXT}</p>
        </div>
      </DialogModal>
    </>
  );
}

UnknownLicense.propTypes = {
  label: PropTypes.string.isRequired,
  title: PropTypes.string.isRequired,
};

/** Licence of the video in the date bar (``material == 'other'``). */
function OtherLicense({ licenses }) {
  const license = licenses[0].license;
  let content;
  if (!license) {
    content = <UnknownLicense label="Unknown" title="Unknown" />;
  } else if (license === "CERN") {
    content = (
      <a target="_blank" rel="noreferrer" href="http://copyright.web.cern.ch/">
        Conditions of Use
      </a>
    );
  } else if (license === "unknown") {
    content = (
      <UnknownLicense label="Unknown Licence" title="Unknown Licence" />
    );
  } else if (licenses[0].url) {
    content = (
      <a target="_blank" rel="noreferrer" href={licenses[0].url}>
        {license}
      </a>
    );
  } else {
    content = <span>{license}</span>;
  }
  return (
    <Tooltip html="License">
      <li>
        <i className="fa fa-certificate text-muted" /> <span>{content}</span>
      </li>
    </Tooltip>
  );
}

OtherLicense.propTypes = { licenses: PropTypes.array.isRequired };

function Translations({ record }) {
  const [open, setOpen] = useState(false);
  const translations = get(record, "metadata.translations") || [];
  return (
    <>
      {translations.length > 0 && (
        <Tooltip html="Title and description are available in more languages, please click to see them all.">
          <a
            className="f8"
            href="#translations"
            onClick={(e) => {
              e.preventDefault();
              setOpen(true);
            }}
          >
            <i className="fa fa-info-circle" />
          </a>
        </Tooltip>
      )}
      <DialogModal
        open={open}
        onClose={() => setOpen(false)}
        title="Available translations"
      >
        {translations.map((translation, index) => (
          <div key={index}>
            <strong>{isoToLanguage(translation.language)}</strong>
            <h4>{get(translation, "title.title")}</h4>
            <Html
              as="p"
              html={sanitize(translation.description) || "No description"}
            />
          </div>
        ))}
      </DialogModal>
    </>
  );
}

Translations.propTypes = { record: PropTypes.object.isRequired };

function ChaptersSection({ chapters, chapterFrames, onViewAll, onJump }) {
  return (
    <div className="cds-detail-chapters px-20 mb-10">
      <hr />
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "10px",
        }}
      >
        <h3>
          <strong>Chapters</strong>
        </h3>
        <button
          type="button"
          className="ui small basic button transcription-button"
          onClick={onViewAll}
        >
          View All
        </button>
      </div>
      <div
        className="chapters-main-horizontal"
        style={{ overflowX: "auto", overflowY: "hidden", whiteSpace: "nowrap" }}
      >
        <div
          style={{
            display: "inline-flex",
            gap: "15px",
            paddingBottom: "8px",
            paddingTop: "8px",
          }}
        >
          {chapters.map((chapter, index) => (
            <HorizontalChapter
              key={`${index}-${chapter.seconds}`}
              chapter={chapter}
              frame={chapterFrames[chapter.seconds]}
              onJump={onJump}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

ChaptersSection.propTypes = {
  chapters: PropTypes.array.isRequired,
  chapterFrames: PropTypes.object.isRequired,
  onViewAll: PropTypes.func.isRequired,
  onJump: PropTypes.func.isRequired,
};

function HorizontalChapter({ chapter, frame, onJump }) {
  const [hover, setHover] = useState(false);
  const [failed, setFailed] = useState(false);
  return (
    <div
      className="chapter-item-horizontal-main"
      onClick={() => onJump(chapter.seconds)}
      onKeyDown={(e) => e.key === "Enter" && onJump(chapter.seconds)}
      onMouseOver={() => setHover(true)}
      onMouseOut={() => setHover(false)}
      onFocus={() => setHover(true)}
      onBlur={() => setHover(false)}
      role="button"
      tabIndex={0}
      style={{
        display: "inline-block",
        cursor: "pointer",
        width: "213px",
        flexShrink: 0,
        padding: "12px",
        border: `1px solid ${hover ? "#2196F3" : "#e1e8ed"}`,
        borderRadius: "8px",
        transition: "all 0.2s ease",
        backgroundColor: hover ? "#f8f9fa" : "white",
        transform: hover ? "translateY(-2px)" : "translateY(0)",
      }}
    >
      <div
        className="chapter-thumbnail-main-horizontal"
        style={{
          width: "189px",
          height: "106px",
          borderRadius: "6px",
          overflow: "hidden",
          backgroundColor: "#f5f5f5",
          marginBottom: "8px",
          position: "relative",
        }}
      >
        {frame && !failed && (
          <img
            src={`/api/iiif/v2/${frame.bucket_id}:${frame.version_id}:${frame.key}/full/320,180/0/default.jpg`}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
            alt={`Chapter ${chapter.timestamp}`}
            onError={() => setFailed(true)}
          />
        )}
        {!frame && (
          <div
            style={{
              width: "100%",
              height: "100%",
              backgroundColor: "#e9ecef",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <i
              className="fa fa-film"
              style={{ color: "#6c757d", fontSize: "20px" }}
            />
          </div>
        )}
        <div
          style={{
            position: "absolute",
            bottom: "4px",
            right: "4px",
            backgroundColor: "rgba(0,0,0,0.8)",
            color: "white",
            padding: "2px 4px",
            borderRadius: "2px",
            fontSize: "11px",
            fontWeight: 500,
          }}
        >
          {chapter.timestamp}
        </div>
      </div>
      <div className="chapter-info-main-horizontal">
        <div
          style={{
            fontSize: "13px",
            fontWeight: 600,
            lineHeight: 1.3,
            color: "#333",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "normal",
            display: "-webkit-box",
            WebkitLineClamp: 2,
            lineClamp: 2,
            WebkitBoxOrient: "vertical",
            maxHeight: "2.6em",
          }}
        >
          {cleanHtmlFromTitle(chapter.title)}
        </div>
      </div>
    </div>
  );
}

HorizontalChapter.propTypes = {
  chapter: PropTypes.object.isRequired,
  frame: PropTypes.object,
  onJump: PropTypes.func.isRequired,
};

HorizontalChapter.defaultProps = { frame: null };

/** The video player, with a placeholder until its page has loaded. */
function PlayerFrame({ title, src }) {
  const [loadedSrc, setLoadedSrc] = useState(null);
  return (
    <>
      <iframe
        title={title}
        scrolling="no"
        width="100%"
        height="100%"
        frameBorder="0"
        src={src}
        allowFullScreen
        onLoad={() => setLoadedSrc(src)}
      />
      {loadedSrc !== src && (
        <Placeholder
          inverted
          className="cds-placeholder cds-placeholder-black cds-placeholder-player-overlay"
        >
          <Placeholder.Image />
        </Placeholder>
      )}
    </>
  );
}

PlayerFrame.propTypes = {
  title: PropTypes.string.isRequired,
  src: PropTypes.string.isRequired,
};

export function VideoDetail({
  record,
  recordViews,
  previewLines,
  relatedQueryUrl,
  onDownload,
}) {
  const metadata = record.metadata;
  const master = findMaster(record);
  const subtitles = getVttSubtitles(record);
  const hasTranscripts = subtitles.length > 0;
  const chapters = useMemo(() => metadata.chapters || [], [metadata.chapters]);
  const chapterFrames = useMemo(
    () => buildChapterFrames(record, chapters),
    [record, chapters]
  );
  const { shortDescription, fullDescription } = useMemo(
    () => prepareDescriptions(metadata.description, previewLines),
    [metadata.description, previewLines]
  );
  const groupedRelatedIdentifiers = useMemo(
    () => prepareRelatedIdentifiers(metadata),
    [metadata]
  );

  const [showInThisVideoSection, setShowInThisVideoSection] = useState(false);
  const [activeTab, setActiveTab] = useState(
    chapters.length > 0
      ? "chapters"
      : hasTranscripts
      ? "transcript"
      : "chapters"
  );
  const [showFullDescription, setShowFullDescription] = useState(false);
  const [transcriptsByLanguage, setTranscriptsByLanguage] = useState({});
  const [selectedTranscriptLanguage, setSelectedTranscriptLanguage] =
    useState(null);
  const [transcript, setTranscript] = useState({});
  const [transcriptSearch, setTranscriptSearch] = useState("");

  // Load the transcripts, the first loaded one is shown
  useEffect(() => {
    let first = true;
    subtitles.forEach((file) => {
      const lang = (file.tags && file.tags.language) || "unknown";
      if (file.links && file.links.self) {
        parseVttFromUrl(file.links.self).then(
          (cues) => {
            setTranscriptsByLanguage((current) => ({
              ...current,
              [lang]: cues,
            }));
            if (first) {
              first = false;
              setTranscript(cues);
              setSelectedTranscriptLanguage(lang);
            }
          },
          (err) => console.error("VTT parsing failed", err)
        );
      } else {
        console.warn("No subtitle file found.");
      }
    });
    // Load once per record
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [record]);

  const filteredTranscript = useMemo(
    () => filterTranscript(transcript, transcriptSearch),
    [transcript, transcriptSearch]
  );
  const { currentTranscriptLine, currentChapter } = usePlayerHighlights(
    transcript,
    chapters
  );

  const jumpToChapter = (timecode) => {
    scrollToElement("videoPlayerSection");
    seekTo(timecode);
  };

  const toggleInThisVideo = (tab) => {
    setShowInThisVideoSection(true);
    setActiveTab(tab);
    scrollToElement("inThisVideoSection");
  };

  const onDescriptionClick = (event) => {
    const link =
      event.target.closest && event.target.closest("a.timestamp-link");
    if (link) {
      event.preventDefault();
      try {
        jumpToChapter(parseInt(link.dataset.seconds, 10));
      } catch (e) {
        console.error("Could not seek to timestamp:", e);
      }
    }
  };

  const withPanel =
    (hasTranscripts || chapters.length > 0) && showInThisVideoSection;
  const licenses = groupBy(metadata.license, "material", "other");
  const contributors = groupBy(metadata.contributors, "role");
  const reportNumber = get(metadata, "report_number[0]");
  const hasIndico =
    angularFilterBy(metadata.related_identifiers, { scheme: "indico" }).length >
    0;

  return (
    <>
      {master && (master.subformat || []).length < 1 && (
        <div id="announcement" className="ui warning message text-center">
          The video might not be playing correctly at the moment due to video
          formats not yet created. Please try again later.
        </div>
      )}
      <div className="cds-detail-video cds-detail-video-wrapper bg-n pb-20">
        {/* Video Section */}
        {/* As before, the metadata are inside the (black) video section */}
        {metadata.recid && master && master.key && (
          <div className="bg-b">
            <div
              className={`video-section${
                showInThisVideoSection ? " cds-container-fluid" : ""
              }`}
              id="videoPlayerSection"
            >
              <div className={withPanel ? "cds-row" : undefined}>
                <div className={withPanel ? "cds-col-md-8 pt-20" : undefined}>
                  <div className="cds-video-iframe text-center">
                    <PlayerFrame
                      title={get(metadata, "title.title") || "Video"}
                      src={previewIframeSrc(metadata.recid, master.key)}
                    />
                  </div>
                </div>
                <InThisVideo
                  visible={withPanel}
                  activeTab={activeTab}
                  onActiveTab={setActiveTab}
                  onClose={() => setShowInThisVideoSection(false)}
                  chapters={chapters}
                  chapterFrames={chapterFrames}
                  hasTranscripts={hasTranscripts}
                  transcriptsByLanguage={transcriptsByLanguage}
                  selectedTranscriptLanguage={selectedTranscriptLanguage}
                  onTranscriptLanguage={(lang) => {
                    setSelectedTranscriptLanguage(lang);
                    if (transcriptsByLanguage[lang]) {
                      setTranscript(transcriptsByLanguage[lang]);
                    } else {
                      console.warn("Transcript not found for language:", lang);
                    }
                  }}
                  transcriptSearch={transcriptSearch}
                  onTranscriptSearch={setTranscriptSearch}
                  filteredTranscript={filteredTranscript}
                  currentTranscriptLine={currentTranscriptLine}
                  currentChapter={currentChapter}
                />
              </div>
            </div>
            {/* Metadata Section */}
            <div className="cds-container-fluid">
              <div className="cds-row">
                {/* Left Column */}
                <div className="cds-col-md-8">
                  <div className="cds-detail cds-detail-video cds-div-shadow bg-w mt-20 pt-10 pb-10">
                    {/* DOI and report number */}
                    <div className="px-20">
                      <div className="cds-row">
                        <div className="cds-col-md-2">
                          <ul
                            className="cds-list-inline"
                            style={{
                              display: get(record, "links.project_edit")
                                ? undefined
                                : "none",
                            }}
                          >
                            <li>
                              <a
                                href={get(record, "links.project_edit")}
                                title="Edit the record"
                              >
                                <i className="fa fa-edit" /> edit
                              </a>
                            </li>
                          </ul>
                        </div>
                        <div className="cds-col-md-10">
                          <ul className="cds-list-inline text-right">
                            {isPublic(metadata) ? (
                              <li>
                                <Tooltip html="This record is <b>public</b>.">
                                  <span className="ui label cds-label cds-label-success">
                                    Public
                                  </span>
                                </Tooltip>
                              </li>
                            ) : (
                              <li>
                                <Tooltip html="This record is <b>restricted</b>.">
                                  <span className="ui label cds-label cds-label-warning">
                                    Restricted
                                  </span>
                                </Tooltip>
                              </li>
                            )}{" "}
                            {metadata.doi && (
                              <li>
                                <DoiBadge record={record} />
                              </li>
                            )}{" "}
                            {reportNumber && (
                              <li className="pr-0">
                                <ReportNumberBadge record={record} />
                              </li>
                            )}{" "}
                          </ul>
                        </div>
                      </div>
                    </div>
                    {/* Title */}
                    <div className="cds-detail-title cds-detail-video-title mt-20 px-20">
                      <hgroup>
                        <h1 className="mb-0 mt-0 f4 fw-n t-b">
                          {get(metadata, "title.title")}{" "}
                          <Translations record={record} />
                        </h1>
                      </hgroup>
                    </div>
                    {/* Date & Views */}
                    <div className="cds-detail-date cds-detail-video-date mb-30 px-20 my-20 f8">
                      <ul className="cds-list-inline mb-0">
                        <Tooltip html="Copyright">
                          <li>
                            <i className="fa fa-copyright text-muted" />{" "}
                            {get(metadata, "copyright.year")}{" "}
                            {get(metadata, "copyright.holder")}
                          </li>
                        </Tooltip>{" "}
                        {Object.entries(licenses)
                          .filter(([material]) => material === "other")
                          .map(([material, items]) => (
                            <OtherLicense key={material} licenses={items} />
                          ))}{" "}
                        <Tooltip html="Date">
                          <li>
                            <i className="fa fa-calendar text-muted" />{" "}
                            {formatDate(metadata.date, "dd MMMM yyyy")}
                          </li>
                        </Tooltip>{" "}
                        <Tooltip html="Video duration">
                          <li>
                            <i className="fa fa-clock-o text-muted" />{" "}
                            {replace(metadata.duration, ".000", "")}
                          </li>
                        </Tooltip>{" "}
                        <li className="pull-right">{recordViews || 0} Views</li>
                      </ul>
                    </div>
                    <hr />
                    {/* Description */}
                    <div
                      className="cds-detail-description cds-detail-video-description t-b px-20"
                      onClick={onDescriptionClick}
                      role="presentation"
                    >
                      <Html
                        as="p"
                        className="mb-30"
                        html={
                          sanitize(
                            showFullDescription
                              ? fullDescription
                              : shortDescription
                          ) || "No description"
                        }
                      />
                      {/* Hidden content */}
                      <div
                        className="mt-20"
                        style={{
                          display: showFullDescription ? undefined : "none",
                        }}
                      >
                        {/* Contributors */}
                        <div className="mb-20">
                          <p>
                            <strong>Contributors</strong>
                          </p>
                          {Object.entries(contributors).map(
                            ([role, contribs]) => (
                              <div className="pl-10" key={role}>
                                <p>{role}: </p>
                                <ul>
                                  {contribs.map((contrib, index) => (
                                    <li key={index}>
                                      <a
                                        href={`/search?q=contributors.name:"${contrib.name}"`}
                                      >
                                        {contrib.name}
                                      </a>{" "}
                                      {contrib.affiliations
                                        ? " - " + contrib.affiliations.join(",")
                                        : ""}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )
                          )}
                        </div>
                        <div className="mb-10">
                          {/* License */}
                          {(metadata.license || []).length > 1 && (
                            <div className="mb-0">
                              <p>
                                <strong>Licences</strong>
                              </p>
                              {Object.entries(licenses)
                                .filter(([material]) => material !== "other")
                                .map(([material, items]) => (
                                  <div className="pl-10" key={material}>
                                    <p>{material}:</p>
                                    <ul>
                                      {items
                                        .filter(
                                          (license) =>
                                            license.license || license.credit
                                        )
                                        .map((license, index) => (
                                          <li key={index}>
                                            {license.credit && (
                                              <span>{license.credit}</span>
                                            )}
                                            {!license.credit &&
                                              license.license && (
                                                <span>
                                                  <a
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    href={license.url}
                                                  >
                                                    {license.license}
                                                  </a>
                                                </span>
                                              )}
                                          </li>
                                        ))}
                                    </ul>
                                  </div>
                                ))}
                            </div>
                          )}
                          <div className="mt-30">
                            <ul className="cds-list-inline pt-20 f8">
                              {metadata.language && (
                                <Tooltip html="Video Language">
                                  <li>
                                    <i className="fa fa-globe text-muted" />{" "}
                                    <a
                                      href={`/search?q=language:"${metadata.language}"`}
                                    >
                                      {isoToLanguage(metadata.language)}
                                    </a>
                                  </li>
                                </Tooltip>
                              )}{" "}
                              {metadata.language &&
                                (get(record, "links.project_html") ||
                                  metadata._project_id) && <li>·</li>}{" "}
                              {(get(record, "links.project_html") ||
                                metadata._project_id) && (
                                <li>
                                  <i className="fa fa-list-ul text-muted" />{" "}
                                  <a
                                    href={
                                      get(record, "links.project_html") ||
                                      "/search?q=_project_id:" +
                                        metadata._project_id
                                    }
                                  >
                                    More videos in the project
                                  </a>
                                </li>
                              )}
                            </ul>
                          </div>
                        </div>
                      </div>
                      {/* Related links */}
                      {(metadata.related_links || []).length > 0 && (
                        <div>
                          <strong>Related links</strong>
                          {metadata.related_links.map((relatedLink, index) => (
                            <ul key={index}>
                              <li>
                                <a
                                  href={absoluteURL(relatedLink.url)}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  {relatedLink.name}
                                </a>
                              </li>
                            </ul>
                          ))}
                        </div>
                      )}
                      {/* Related identifiers */}
                      {!isEmpty(groupedRelatedIdentifiers) && (
                        <div>
                          <strong>Related identifiers</strong>
                          <ul>
                            {Object.entries(groupedRelatedIdentifiers).map(
                              ([relationType, items]) => (
                                <li key={relationType}>
                                  <strong>
                                    {formatRelationResourceType(relationType)}
                                  </strong>
                                  <ul>
                                    {items.map((ri, index) => (
                                      <li key={index}>
                                        {ri.resource_type && (
                                          <span>
                                            {formatRelationResourceType(
                                              ri.resource_type
                                            )}
                                            :{" "}
                                          </span>
                                        )}
                                        <a
                                          className="cds-text-break"
                                          href={ri.url}
                                          target="_blank"
                                          rel="noreferrer"
                                        >
                                          {ri.identifier}
                                        </a>{" "}
                                        ({ri.scheme})
                                      </li>
                                    ))}
                                  </ul>
                                </li>
                              )
                            )}
                          </ul>
                        </div>
                      )}
                      <div
                        className="text-center"
                        style={{
                          display: showFullDescription ? "none" : undefined,
                        }}
                      >
                        <button
                          type="button"
                          className="cds-btn-link cds-btn-sm"
                          onClick={() =>
                            setShowFullDescription(!showFullDescription)
                          }
                        >
                          {showFullDescription ? "Show less" : "Show more"}
                        </button>
                      </div>
                    </div>

                    {/* Chapters Section */}
                    {chapters.length > 0 && (
                      <ChaptersSection
                        chapters={chapters}
                        chapterFrames={chapterFrames}
                        onViewAll={() => toggleInThisVideo("chapters")}
                        onJump={jumpToChapter}
                      />
                    )}

                    {/* More */}
                    <div className="cds-detail-more cds-detail-video-more px-20">
                      <div
                        className="mb-20"
                        style={{ display: hasTranscripts ? undefined : "none" }}
                      >
                        <hr />
                        <div className="transcription-text">
                          <h3>
                            <strong>Transcriptions</strong>
                          </h3>
                          <small className="text-muted">
                            Follow along or search within the transcript.
                          </small>
                        </div>
                        <div className="transcription-button-wrapper pt-10">
                          <button
                            type="button"
                            className="ui small basic button transcription-button"
                            onClick={() => toggleInThisVideo("transcript")}
                          >
                            Show Transcriptions
                          </button>
                        </div>
                      </div>
                      {hasIndico && (
                        <RelatedEventSection
                          record={record}
                          relatedQueryUrl={relatedQueryUrl}
                        />
                      )}
                    </div>
                  </div>
                  <div className="cds-detail cds-detail-video cds-div-shadow bg-gl bt bw-1 bc-ccc pt-10 pb-20 px-20">
                    <div className="cds-detail-title cds-detail-video-title">
                      <h3 className="cds-title-section-decoration bt bw-1 pt-10 mb-20">
                        <i className="fa fa-share" /> Share
                      </h3>
                    </div>
                    <Share record={record} />
                  </div>
                </div>
                {/* Right Column */}
                <div className="cds-col-md-4">
                  <div className="cds-detail cds-detail-video cds-div-shadow bg-w pt-10 px-20 pb-10 mb-30 mt-20 t-b">
                    <Downloads record={record} onDownload={onDownload} />
                  </div>
                  <Keywords record={record} />
                  <div className="cds-detail cds-detail-video cds-div-shadow bg-w pt-10 px-20 pb-10 mb-30 mt-20 t-b">
                    <TechnicalMetadata record={record} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

VideoDetail.propTypes = {
  record: PropTypes.object.isRequired,
  recordViews: PropTypes.number,
  previewLines: PropTypes.number.isRequired,
  relatedQueryUrl: PropTypes.string,
  onDownload: PropTypes.func.isRequired,
};

VideoDetail.defaultProps = { recordViews: undefined, relatedQueryUrl: "" };
