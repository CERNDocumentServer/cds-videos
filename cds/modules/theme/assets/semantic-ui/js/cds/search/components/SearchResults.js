/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Results of a search, rendered with one of the video templates. */

import React from "react";
import PropTypes from "prop-types";

import { useSearch } from "../hooks";
import { isFirstLoad } from "./SearchStatus";

/**
 * Results of the search rendered by a template component, or its
 * placeholder while the search is loading.
 */
export function SearchResults({
  template: Template,
  placeholder: TemplatePlaceholder = null,
  ...props
}) {
  const [state] = useSearch();
  if (TemplatePlaceholder && (state.loading || isFirstLoad(state))) {
    return <TemplatePlaceholder args={state.args} />;
  }
  return <Template results={state.results} args={state.args} {...props} />;
}

SearchResults.propTypes = {
  template: PropTypes.elementType.isRequired,
  placeholder: PropTypes.elementType,
};
