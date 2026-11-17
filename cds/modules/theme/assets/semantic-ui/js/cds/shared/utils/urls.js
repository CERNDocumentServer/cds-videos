/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Build the URLs of downloads, shares and previews. */

/** Transform an URL into an absolute URL. */
export function absoluteURL(url) {
  if (url.startsWith("https://") || url.startsWith("http://")) {
    return url;
  }
  return "http://" + url;
}

/** Format urls for download. */
export function download(url) {
  if (!url) {
    return url;
  }
  const re = /([?&].*)=[^?&]+/;
  if (url.match(re)) {
    return url + "&download";
  }
  return url + "?download";
}

/** Share URLs (see https://github.com/bradvin/social-share-urls). */
export function assembleShareURL(record, platform) {
  if (!record) {
    return undefined;
  }
  const title = encodeURIComponent(record.metadata.title.title);
  const description = encodeURIComponent(record.metadata.description);
  const currentPageAddress = encodeURIComponent(window.location.href);
  const platformMapping = {
    facebook: "https://www.facebook.com/sharer.php?u=" + currentPageAddress,
    twitter:
      "https://twitter.com/intent/tweet?url=" +
      currentPageAddress +
      "&text=" +
      title +
      "&hashtags=cern",
    linkedin:
      "https://www.linkedin.com/shareArticle?mini=true&url=" +
      currentPageAddress +
      "&title=" +
      title +
      "&summary=" +
      description +
      "&source=" +
      currentPageAddress,
    reddit:
      "https://reddit.com/submit?url=" + currentPageAddress + "&title=" + title,
    email:
      "mailto:?subject=" +
      title +
      "&body=" +
      description +
      "%0a" +
      currentPageAddress,
  };
  return platformMapping[platform];
}

/** Iframe embed code of a video (``previewIframe`` filter). */
export function previewIframe(reportNumber, external) {
  let url = "/video/" + reportNumber;
  if (external) {
    url = window.location.origin + url;
  }
  return (
    '<iframe scrolling="no"  src="' +
    url +
    '" width="560" height="315" frameborder="0" allowfullscreen></iframe>'
  );
}

/** Source of the preview iframe of a record (``previewIframeSrc`` filter). */
export function previewIframeSrc(id, key, external) {
  let url = "/record/" + id + "/preview/" + key;
  const timestamp = new URLSearchParams(window.location.search).get("t");
  if (timestamp) {
    url += "?t=" + timestamp;
  }
  if (external) {
    url = window.location.origin + url;
  }
  return url;
}
