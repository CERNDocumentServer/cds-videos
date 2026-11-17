/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* Share and embed links of a video. */

import React, { useState } from "react";
import PropTypes from "prop-types";

import { CopyButton } from "@js/cds/shared/components/CopyButton";
import { get } from "@js/cds/shared/utils/collections";
import { assembleShareURL, previewIframe } from "@js/cds/shared/utils/urls";

import { convertToMinutesSeconds, getPlayer, parseHMS } from "./playback";

function currentPageLink() {
  return window.location.href.split("?")[0];
}

function shareLink(withStart, startInput) {
  let url = currentPageLink();
  if (withStart) {
    const secs = parseHMS(startInput);
    if (!isNaN(secs) && secs > 0) {
      url += (url.indexOf("?") === -1 ? "?" : "&") + "t=" + Math.floor(secs);
    }
  }
  return url;
}

const ICONS = {
  facebook:
    "M18.77 7.46H14.5v-1.9c0-.9.6-1.1 1-1.1h3V.5h-4.33C10.24.5 9.5 3.44 9.5 5.32v2.15h-3v4h3v12h5v-12h3.85l.42-4z",
  twitter:
    "M23.44 4.83c-.8.37-1.5.38-2.22.02.93-.56.98-.96 1.32-2.02-.88.52-1.86.9-2.9 1.1-.82-.88-2-1.43-3.3-1.43-2.5 0-4.55 2.04-4.55 4.54 0 .36.03.7.1 1.04-3.77-.2-7.12-2-9.36-4.75-.4.67-.6 1.45-.6 2.3 0 1.56.8 2.95 2 3.77-.74-.03-1.44-.23-2.05-.57v.06c0 2.2 1.56 4.03 3.64 4.44-.67.2-1.37.2-2.06.08.58 1.8 2.26 3.12 4.25 3.16C5.78 18.1 3.37 18.74 1 18.46c2 1.3 4.4 2.04 6.97 2.04 8.35 0 12.92-6.92 12.92-12.93 0-.2 0-.4-.02-.6.9-.63 1.96-1.22 2.56-2.14z",
  linkedin:
    "M6.5 21.5h-5v-13h5v13zM4 6.5C2.5 6.5 1.5 5.3 1.5 4s1-2.4 2.5-2.4c1.6 0 2.5 1 2.6 2.5 0 1.4-1 2.5-2.6 2.5zm11.5 6c-1 0-2 1-2 2v7h-5v-13h5V10s1.6-1.5 4-1.5c3 0 5 2.2 5 6.3v6.7h-5v-7c0-1-1-2-2-2z",
  reddit:
    "M24 11.5c0-1.65-1.35-3-3-3-.96 0-1.86.48-2.42 1.24-1.64-1-3.75-1.64-6.07-1.72.08-1.1.4-3.05 1.52-3.7.72-.4 1.73-.24 3 .5C17.2 6.3 18.46 7.5 20 7.5c1.65 0 3-1.35 3-3s-1.35-3-3-3c-1.38 0-2.54.94-2.88 2.22-1.43-.72-2.64-.8-3.6-.25-1.64.94-1.95 3.47-2 4.55-2.33.08-4.45.7-6.1 1.72C4.86 8.98 3.96 8.5 3 8.5c-1.65 0-3 1.35-3 3 0 1.32.84 2.44 2.05 2.84-.03.22-.05.44-.05.66 0 3.86 4.5 7 10 7s10-3.14 10-7c0-.22-.02-.44-.05-.66 1.2-.4 2.05-1.54 2.05-2.84zM2.3 13.37C1.5 13.07 1 12.35 1 11.5c0-1.1.9-2 2-2 .64 0 1.22.32 1.6.82-1.1.85-1.92 1.9-2.3 3.05zm3.7.13c0-1.1.9-2 2-2s2 .9 2 2-.9 2-2 2-2-.9-2-2zm9.8 4.8c-1.08.63-2.42.96-3.8.96-1.4 0-2.74-.34-3.8-.95-.24-.13-.32-.44-.2-.68.15-.24.46-.32.7-.18 1.83 1.06 4.76 1.06 6.6 0 .23-.13.53-.05.67.2.14.23.06.54-.18.67zm.2-2.8c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm5.7-2.13c-.38-1.16-1.2-2.2-2.3-3.05.38-.5.97-.82 1.6-.82 1.1 0 2 .9 2 2 0 .84-.53 1.57-1.3 1.87z",
  email:
    "M22 4H2C.9 4 0 4.9 0 6v12c0 1.1.9 2 2 2h20c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zM7.25 14.43l-3.5 2c-.08.05-.17.07-.25.07-.17 0-.34-.1-.43-.25-.14-.24-.06-.55.18-.68l3.5-2c.24-.14.55-.06.68.18.14.24.06.55-.18.68zm4.75.07c-.1 0-.2-.03-.27-.08l-8.5-5.5c-.23-.15-.3-.46-.15-.7.15-.22.46-.3.7-.14L12 13.4l8.23-5.32c.23-.15.54-.08.7.15.14.23.07.54-.16.7l-8.5 5.5c-.08.04-.17.07-.27.07zm8.93 1.75c-.1.16-.26.25-.43.25-.08 0-.17-.02-.25-.07l-3.5-2c-.24-.13-.32-.44-.18-.68s.44-.32.68-.18l3.5 2c.24.13.32.44.18.68z",
};

function SocialButton({ record, platform }) {
  return (
    <a
      className="resp-sharing-button__link"
      href={assembleShareURL(record, platform)}
      target={platform === "email" ? "_self" : "_blank"}
      rel="noreferrer"
      aria-label=""
    >
      <div
        className={`resp-sharing-button resp-sharing-button--${platform} resp-sharing-button--small`}
      >
        <div
          aria-hidden="true"
          className="resp-sharing-button__icon resp-sharing-button__icon--solid"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <path d={ICONS[platform]} />
          </svg>
        </div>
      </div>
    </a>
  );
}

SocialButton.propTypes = {
  record: PropTypes.object.isRequired,
  platform: PropTypes.string.isRequired,
};

export function Share({ record }) {
  const [withStart, setWithStart] = useState(false);
  const [startInput, setStartInput] = useState("0:00");
  const [link, setLink] = useState(currentPageLink);

  const onToggleStart = (event) => {
    const checked = event.target.checked;
    let start = "0:00";
    if (checked) {
      const player = getPlayer();
      if (player) {
        start = convertToMinutesSeconds(player.currentTime);
      } else {
        start = startInput;
      }
    }
    setWithStart(checked);
    setStartInput(start);
    setLink(shareLink(checked, start));
  };

  const onChangeStart = (event) => {
    const value = event.target.value;
    setStartInput(value);
    // An invalid start time counts as none
    setLink(shareLink(withStart, /^[0-9:]*$/.test(value) ? value : undefined));
  };

  return (
    <>
      {/* Share link */}
      <div className="cds-detail-sharelink mb-20 d-flex align-items-center">
        <div className="ui fluid action input cds-input-group">
          <input
            id="copyShare"
            type="text"
            value={link}
            readOnly
            aria-label="Shareable link"
          />
          <CopyButton targetId="copyShare" />
        </div>
        <div className="sharelink-start">
          <label className="start-checkbox" htmlFor="cds-share-start">
            <input
              id="cds-share-start"
              type="checkbox"
              checked={withStart}
              onChange={onToggleStart}
            />
            Start at:
          </label>
          <input
            type="text"
            className="start-time"
            placeholder="0:00"
            disabled={!withStart}
            value={startInput}
            onChange={onChangeStart}
          />
        </div>
      </div>

      {/* Social */}
      <div className="cds-detail-video-social-media mb-20">
        <h4>Social media</h4>
        {["facebook", "twitter", "linkedin", "reddit", "email"].map(
          (platform) => (
            // The buttons were separated by whitespace, except the LinkedIn
            // and Reddit ones (adjacent in the former template)
            <React.Fragment key={platform}>
              <SocialButton record={record} platform={platform} />
              {platform === "linkedin" ? null : " "}
            </React.Fragment>
          )
        )}
      </div>

      {/* Embed */}
      <div className="cds-detail-video-embed">
        <h4>Embed</h4>
        <div className="ui fluid action input cds-input-group">
          <input
            id="copyEmbed"
            type="text"
            defaultValue={previewIframe(
              get(record, "metadata.report_number[0]"),
              true
            )}
          />
          <CopyButton targetId="copyEmbed" />
        </div>
        <div className="cds-video-embed-faq mt-10">
          <a href="/faq#embed-options">Read more about embed options</a>
        </div>
      </div>
    </>
  );
}

Share.propTypes = { record: PropTypes.object.isRequired };
