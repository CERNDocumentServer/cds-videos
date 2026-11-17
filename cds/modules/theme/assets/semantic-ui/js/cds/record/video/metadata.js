/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Prepare the title, descriptions and related identifiers of a video. */

/** Remove the HTML tags of a chapter title. */
export function cleanHtmlFromTitle(title) {
  if (!title) return title;
  let cleanTitle = title.replace(/<[^>]+>/g, " ");
  cleanTitle = cleanTitle.replace(/\s+/g, " ").trim();
  return cleanTitle;
}

/**
 * Turn the timestamps of a description (``0:00``, ``00:00:00``...) into
 * links seeking the player. The clicks are handled by the description
 * container (``data-seconds``).
 */
export function processDescriptionWithClickableTimestamps(description) {
  if (!description) return description;
  const pattern = /(\d{1,2}:(?:\d{1,2}:)?\d{1,2})/g;
  return description.replace(pattern, (match) => {
    const timeParts = match.split(":");
    let totalSeconds;
    if (timeParts.length === 2) {
      const [minutes, seconds] = timeParts.map(Number);
      totalSeconds = minutes * 60 + seconds;
    } else if (timeParts.length === 3) {
      const [hours, minutes, seconds] = timeParts.map(Number);
      totalSeconds = hours * 3600 + minutes * 60 + seconds;
    } else {
      return match;
    }
    return `<a href="javascript:void(0)" class="timestamp-link" data-seconds="${totalSeconds}" style="color: #2196F3; font-weight: 600; cursor: pointer;">${match}</a>`;
  });
}

/** Short (first lines) and full descriptions with clickable timestamps. */
export function prepareDescriptions(description, previewLines) {
  if (!description) {
    return {
      shortDescription: "No description",
      fullDescription: "No description",
    };
  }
  const lines = description.split(/\r?\n/);
  const firstLines = lines.slice(0, previewLines).join("\n");
  return {
    shortDescription: processDescriptionWithClickableTimestamps(firstLines),
    fullDescription: processDescriptionWithClickableTimestamps(description),
  };
}

/** Related identifiers grouped by relation type (without Indico ones). */
export function prepareRelatedIdentifiers(metadata) {
  const grouped = {};
  (metadata.related_identifiers || []).forEach((original) => {
    if (original.scheme === "Indico") return;
    const item = { ...original };
    switch (item.scheme) {
      case "URL":
        item.url = item.identifier;
        break;
      case "CDS":
        item.url = `https://cds.cern.ch/record/${item.identifier}`;
        break;
      case "DOI":
        item.url = `https://doi.org/${item.identifier}`;
        break;
      default:
        return;
    }
    if (!grouped[item.relation_type]) {
      grouped[item.relation_type] = [];
    }
    grouped[item.relation_type].push(item);
  });
  return grouped;
}
