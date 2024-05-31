import $ from "jquery";
import * as inveniographs from "invenio-charts-js";

function getStats(record) {
  const defaultConfig = {
    legend: {
      visible: false,
    },
    tooltip: {
      enabled: false,
    },
  };

  fetchRecordData(record.recid, "pageviews", defaultConfig); // fetch the pageviews for a record
  fetchRecordData(record.recid, "downloads", defaultConfig); // fetch the downloads for a record
}

async function fetchRecordData(recordId, category, defaultConfig) {
  try {
    var resp = await $.ajax({
      type: "GET",
      url: "/api/stats/" + recordId,
      headers: {
        "Content-Type": "application/json",
      },
    });
    $("#" + category + "-loading-spinner").hide();
    new inveniographs.LineGraph(resp.data, category, defaultConfig).render();
  } catch (error) {
    console.log(error);
    $("#" + category + "-loading-spinner").hide();
    $("#" + category + "-error-message").show();
  }
}

window.getStats = getStats;
