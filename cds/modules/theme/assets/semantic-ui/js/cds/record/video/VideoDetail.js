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
 * The video page. ``VideoDetail`` holds the state of the page (the "In this
 * video" panel, the expanded description, the transcripts and the playback
 * highlights) and lays out the sections, which only render their props.
 */

import React, { useMemo, useState } from "react";
import PropTypes from "prop-types";

import { filterByFields } from "@js/cds/shared/utils/collections";
import { findMaster, getVttSubtitles } from "@js/cds/shared/utils/records";

import { buildChapterFrames, scrollToElement, seekTo } from "./playback";
import { prepareDescriptions, prepareRelatedIdentifiers } from "./metadata";
import { useTranscripts } from "./useTranscripts";
import { InThisVideo, usePlayerHighlights } from "./InThisVideo";
import { VideoPlayerSection } from "./VideoPlayerSection";
import { VideoHeader } from "./VideoHeader";
import { VideoDescription } from "./VideoDescription";
import { ChaptersSection } from "./Chapters";
import { TranscriptsTeaser } from "./TranscriptsTeaser";
import { RelatedEventSection } from "./RelatedEventSection";
import { Share } from "./Share";
import { Downloads } from "./Downloads";
import { TechnicalMetadata } from "./TechnicalMetadata";
import { Keywords } from "../components/Keywords";

export function VideoDetail({
  record,
  recordViews = undefined,
  previewLines,
  relatedQueryUrl = "",
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
  const {
    transcriptsByLanguage,
    selectedTranscriptLanguage,
    selectTranscriptLanguage,
    transcript,
    transcriptSearch,
    setTranscriptSearch,
    filteredTranscript,
  } = useTranscripts(record, subtitles);
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

  const withPanel =
    (hasTranscripts || chapters.length > 0) && showInThisVideoSection;
  const hasIndico =
    filterByFields(metadata.related_identifiers, { scheme: "indico" }).length >
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
        {/* As before, the metadata are inside the (black) video section */}
        {metadata.recid && master && master.key && (
          <div className="bg-b">
            <VideoPlayerSection
              metadata={metadata}
              master={master}
              panelOpen={showInThisVideoSection}
              withPanel={withPanel}
            >
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
                onTranscriptLanguage={selectTranscriptLanguage}
                transcriptSearch={transcriptSearch}
                onTranscriptSearch={setTranscriptSearch}
                filteredTranscript={filteredTranscript}
                currentTranscriptLine={currentTranscriptLine}
                currentChapter={currentChapter}
              />
            </VideoPlayerSection>
            <div className="cds-container-fluid">
              <div className="cds-row">
                {/* Left Column */}
                <div className="cds-col-md-8">
                  <div className="cds-detail cds-detail-video cds-div-shadow bg-w mt-20 pt-10 pb-10">
                    <VideoHeader record={record} recordViews={recordViews} />
                    <hr />
                    <VideoDescription
                      record={record}
                      shortDescription={shortDescription}
                      fullDescription={fullDescription}
                      groupedRelatedIdentifiers={groupedRelatedIdentifiers}
                      expanded={showFullDescription}
                      onToggle={() =>
                        setShowFullDescription(!showFullDescription)
                      }
                      onJump={jumpToChapter}
                    />

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
                      <TranscriptsTeaser
                        visible={hasTranscripts}
                        onShow={() => toggleInThisVideo("transcript")}
                      />
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
