function getStats(record) {
  const defaultConfig = {
    legend: {
      visible: false,
    },
    tooltip: {
      enabled: false,
    },
  };

  fetchRecordData(record.recid, 'pageviews', defaultConfig); // fetch the pageviews for a record
  fetchRecordData(record.recid, 'downloads', defaultConfig); // fetch the downloads for a record
}

function fetchRecordData(recordId, category, defaultConfig) {
  $.ajax({
    type: 'GET',
    url: `/api/stats/${recordId}/${category}`,
    headers: {
      'Content-Type': 'application/json'
    }
  })
  .success((data) => {
    $(`#${category}-loading-spinner`).hide();
    new inveniographs.LineGraph(data, category, defaultConfig).render();
  })
  .error((error) => {
    $(`#${category}-loading-spinner`).hide();
    $(`#${category}-error-message`).show();
    console.error(`GET: /api/stats/${recordId}/${category}: `, error);
  });
}
