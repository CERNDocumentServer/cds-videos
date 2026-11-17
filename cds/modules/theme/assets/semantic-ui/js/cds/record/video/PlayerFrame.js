/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** The video player iframe, with a placeholder until it loads. */

import React, { useState } from "react";
import PropTypes from "prop-types";
import { Placeholder } from "semantic-ui-react";

/** The video player, with a placeholder until its page has loaded. */
export function PlayerFrame({ title, src }) {
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
