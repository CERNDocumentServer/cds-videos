define(['d3.v3', 'elasticsearch'], function (d3, elasticsearch) {
    "use strict";
    // ELASTICSEARCH QUERY GOES HERE

    // We don't need elastic search query for now
    // var client = new elasticsearch.Client( {
    //     host: 'localhost:9200',
    //     log: 'trace'
    // });

    // D3 CODE GOES HERE

    // Fake dataset
    var dataset = [1, 0, 3, 5, 2, 1, 0, 1, 1, 4, 10, 2, 2, 0, 1, 3, 5, 2]
    d3.select(".histogram")
    .data(dataset)
    .enter()
    .append("div")
    .attr("class", "bar")
    // .style("height", function(d) {
    //     var barHeight = d * 5;
    //     return barHeight + "px";
    // });
});