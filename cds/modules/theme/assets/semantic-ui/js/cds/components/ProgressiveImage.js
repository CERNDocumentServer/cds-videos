/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

import React, { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";

import { NOT_FOUND_IMAGE } from "../utils";

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.src = src;
    img.onload = () => resolve(src);
    img.onerror = () => reject(src);
  });
}

/**
 * Image blurred until loaded, which plays the gif animation of the video on
 * mouse over (``image-progressive-loading`` + ``err-src`` directives).
 */
export function ProgressiveImage({
  imgSrc,
  gifSrc = null,
  className = null,
  errSrc = NOT_FOUND_IMAGE,
}) {
  const [src, setSrc] = useState(imgSrc);
  const [loaded, setLoaded] = useState(false);
  const state = useRef({ over: false, gifLoaded: false, gifError: false });

  useEffect(() => {
    let cancelled = false;
    setSrc(imgSrc);
    setLoaded(false);
    loadImage(imgSrc).then(
      () => {
        if (!cancelled) {
          setLoaded(true);
          setSrc(imgSrc);
        }
      },
      () => {
        // Same as the directive: the image stays blurred
      }
    );
    return () => {
      cancelled = true;
    };
  }, [imgSrc]);

  const onMouseOver = () => {
    if (!gifSrc || state.current.gifError) return;
    state.current.over = true;
    if (!state.current.gifLoaded) {
      loadImage(gifSrc).then(
        () => {
          state.current.gifLoaded = true;
          if (state.current.over) setSrc(gifSrc);
        },
        () => {
          state.current.gifError = true;
        }
      );
    } else {
      setSrc(gifSrc);
    }
  };

  const onMouseLeave = () => {
    if (!gifSrc) return;
    state.current.over = false;
    setSrc(imgSrc);
  };

  const onError = (event) => {
    const fallback = errSrc || NOT_FOUND_IMAGE;
    if (event.target.getAttribute("src") !== fallback) {
      setSrc(fallback);
    }
  };

  return (
    <img
      alt=""
      className={[className, loaded ? null : "cds-blur"]
        .filter(Boolean)
        .join(" ")}
      src={src}
      onMouseOver={onMouseOver}
      onFocus={onMouseOver}
      onMouseLeave={onMouseLeave}
      onBlur={onMouseLeave}
      onError={onError}
    />
  );
}

ProgressiveImage.propTypes = {
  imgSrc: PropTypes.string.isRequired,
  gifSrc: PropTypes.string,
  className: PropTypes.string,
  errSrc: PropTypes.string,
};
