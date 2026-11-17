/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

import { useEffect, useMemo, useState } from "react";

import { filterTranscript, parseVttFromUrl } from "./playback";

/**
 * Transcripts of a video, read from its VTT subtitle files: one per
 * language, the first one loaded is shown, and a search filters its lines.
 */
export function useTranscripts(record, subtitles) {
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

  const selectTranscriptLanguage = (lang) => {
    setSelectedTranscriptLanguage(lang);
    if (transcriptsByLanguage[lang]) {
      setTranscript(transcriptsByLanguage[lang]);
    } else {
      console.warn("Transcript not found for language:", lang);
    }
  };

  return {
    transcriptsByLanguage,
    selectedTranscriptLanguage,
    selectTranscriptLanguage,
    transcript,
    transcriptSearch,
    setTranscriptSearch,
    filteredTranscript,
  };
}
