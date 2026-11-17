/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

import { InvenioSearchApi } from "react-searchkit";

import { setupInterceptors } from "@js/cds/shared/api";
import { hiddenParamsOf, queryStateToParams, toRequestParams } from "./params";

/**
 * Serialize the query state to the REST API parameters used by CDS
 * (``page``, ``size``, ``q``, ``sort`` and one key per filter).
 */
export class CDSRequestSerializer {
  constructor() {
    this.serialize = this.serialize.bind(this);
  }

  serialize(stateQuery) {
    const params = {
      ...queryStateToParams(stateQuery),
      ...hiddenParamsOf(stateQuery),
    };
    return toRequestParams(params);
  }
}

/** Keep the ``links`` of the response, used to show the default sorting. */
export class CDSResponseSerializer {
  constructor() {
    this.serialize = this.serialize.bind(this);
  }

  serialize(payload) {
    const { aggregations, hits, links } = payload || {};
    return {
      aggregations: aggregations || {},
      hits: (hits && hits.hits) || [],
      total: hits ? hits.total : 0,
      links: links || {},
      extras: {},
    };
  }
}

/**
 * react-searchkit search API for the CDS REST endpoints: requests go through
 * the CDS interceptors (loading bar), and the last response links are kept.
 */
export class CDSSearchApi extends InvenioSearchApi {
  constructor({ endpoint, headers = {} }) {
    super({
      axios: { url: endpoint, headers: { ...headers } },
      invenio: {
        requestSerializer: CDSRequestSerializer,
        responseSerializer: CDSResponseSerializer,
      },
    });
    this.links = {};
    this.responses = 0;
  }

  initAxios() {
    super.initAxios();
    setupInterceptors(this.http);
  }

  async search(stateQuery) {
    const response = await super.search(stateQuery);
    this.links = response.links || {};
    this.responses += 1;
    delete response.links;
    return response;
  }
}
