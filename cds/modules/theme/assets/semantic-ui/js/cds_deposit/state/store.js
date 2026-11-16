/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* The Redux store of a deposit page. */

import { applyMiddleware, createStore } from "redux";
import thunk from "redux-thunk";

import { createQueue } from "./actions";
import { setProject } from "./page";
import { depositReducer, initialState } from "./reducer";

/**
 * Store of the page. ``config`` holds the settings of the page,
 * ``project`` the project embedded in it, shown from the first render.
 */
export function createDepositStore(config, project) {
  const store = createStore(
    depositReducer,
    initialState(config),
    // The requests changing deposits run one after the other
    applyMiddleware(thunk.withExtraArgument({ queue: createQueue() }))
  );
  if (project) {
    store.dispatch(setProject(project));
  }
  return store;
}
