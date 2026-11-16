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

import { onPendingRequestsChange } from "../api";

const LATENCY_THRESHOLD = 100;

/**
 * Thin progress bar at the top of the page shown while HTTP requests are
 * running (replaces angular-loading-bar, same look and timings).
 */
export function LoadingBar() {
  const [visible, setVisible] = useState(false);
  const [width, setWidth] = useState(0);
  const timers = useRef({});

  useEffect(() => {
    function clearTimers() {
      Object.values(timers.current).forEach((t) => clearTimeout(t));
      if (timers.current.interval) clearInterval(timers.current.interval);
      timers.current = {};
    }
    const unsubscribe = onPendingRequestsChange((pending) => {
      if (pending > 0) {
        if (timers.current.start || timers.current.interval) {
          return;
        }
        clearTimers();
        timers.current.start = setTimeout(() => {
          timers.current.start = null;
          setVisible(true);
          setWidth(2);
          timers.current.interval = setInterval(() => {
            setWidth((current) => {
              if (current >= 99) return current;
              let rnd;
              if (current < 25) rnd = Math.random() * 3 + 3;
              else if (current < 65) rnd = Math.random() * 3;
              else if (current < 90) rnd = Math.random() * 2;
              else rnd = 0.5;
              return Math.min(99, current + rnd);
            });
          }, 250);
        }, LATENCY_THRESHOLD);
      } else {
        clearTimers();
        setWidth(100);
        timers.current.hide = setTimeout(() => {
          setVisible(false);
          setWidth(0);
        }, 500);
      }
    });
    return () => {
      unsubscribe();
      clearTimers();
    };
  }, []);

  if (!visible) {
    return null;
  }
  return (
    <div id="loading-bar" className="cds-loading-bar">
      <div className="bar" style={{ width: `${width}%` }}>
        <div className="peg" />
      </div>
      <div id="loading-bar-spinner" className="cds-loading-bar-spinner">
        <div className="spinner-icon" />
      </div>
    </div>
  );
}
