/*
 * This file is part of Invenio.
 * Copyright (C) 2015 CERN.
 *
 * Invenio is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the
 * License, or (at your option) any later version.
 *
 * Invenio is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Invenio; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
 */


require([
    'jquery',
    'typeahead',
    'hogan'
  ],
  function($, Bloodhound, Hogan) {

    $(document).ready(function() {

      var $searchForm = $('#cds-main-search');
      var $searchBar = $('.cds-main-search-input');
      var $wrapper = $('.cds-input-inner-icon');
      var $searchIcon = $('.cds-main-search-icon');
      var $searchCollection = $('.cds-main-search-collection-label');

      var bootstrapTabletBreakPoint = 950;

      // Check for bar size
      function searchBarResize() {
        if ($('body').width() <= bootstrapTabletBreakPoint){
          $('body').trigger('cds.search.bar.destroy');
          $searchBar.css('width', '80%');
        } else {
          if (!$searchBar.data('typeahead-init')){
            $('body').trigger('cds.search.bar.init');
          }
          var targetWidth = $wrapper.width() - $searchIcon.width() - $searchCollection.width() - 40;
          $searchBar.css('width', targetWidth);
        }
      }

      // Save the search query before submit
      $searchForm.on('submit', function(ev, options) {
        if (options === undefined){
          ev.preventDefault();
          var cdsQueries = window.localStorage.getItem('cds.searches') || '';
          // Convert to array
          cdsQueries = cdsQueries.split(',');

          // Push the latest query
          var value = $searchBar.val();
          if (cdsQueries.indexOf(value) === -1){
            // Shift previous queries if are more than 4
            if (cdsQueries.length > 2) {
              cdsQueries.shift();
            }
            cdsQueries.push(value);
            window.localStorage.setItem('cds.searches', cdsQueries.join(','));
          }
          $searchForm.trigger('submit', {processed: true});
        }
      });

      function searchBarDestroy() {
        $searchBar.typeahead('destroy');
        $searchBar.off('focus');
        $searchBar.data('typeahead-init', false);
      }

      function searchBarInit() {
        $searchBar.data('typeahead-init', true);
        // FIXME: Move this to a suggestion engine (Obelix)?
        function buildSuggestions () {
          var suggested = [
            {
              type: "retweet",
              label: "CERN Scientific Output",
            },
            {
              type: "retweet",
              label: "CERN Bulletin",
            },
            {
              type: "retweet",
              label: "Videos",
            }
          ];
          // Read previous searches if any
          var cdsQueries = window.localStorage.getItem('cds.searches') || '';
          // Convert to array
          cdsQueries = cdsQueries.split(',');
          $(cdsQueries).each(function(index, item){
            if(item){
              suggested.unshift({
                label: item,
                type: 'history'
              });
            }
          });
          return suggested;
        }

        // Right now nothing to autocomplete
        var suggestionMatcher = new Bloodhound({
          datumTokenizer: Bloodhound.tokenizers.obj.whitespace('label'),
          queryTokenizer: Bloodhound.tokenizers.whitespace,
          local: []
        });

        suggestionMatcher.initialize();

        var compiledTemplate = Hogan.compile(
          '<div class="cds-search-suggestion">{{#type}}<i class="fa fa-{{type}}"></i>{{/type}} {{label}}</div>'
        );

        // Decide if we return the suggested or autocomplete
        function suggestionEngine(q, cb) {
          // If the query is empty show the `suggestions` var
          if( q === ''){
            cb(buildSuggestions());
          } else {
            cb(suggestionMatcher.get(q));
          }
        }
        // Initialise typeahead
        $searchBar.typeahead({
          hint: false,
          highlight: true,
          minLength: 0
        },
        {
          name: 'states',
          display: 'label',
          source: suggestionEngine,
          templates: {
            suggestion: compiledTemplate.render.bind(compiledTemplate)
          },
        });

        // When the searchbar is on focus force display the suggestions.
        $searchBar.on('focus', function() {
          if($(this).val() === '') {
            $(this).data().ttTypeahead.input.trigger('queryChanged', '');
          }
        });
      }

      // Bind searchbar resize event
      $('body').on('cds.search.bar.init', searchBarInit);
      $('body').on('cds.search.bar.resize', searchBarResize);
      $('body').on('cds.search.bar.destroy', searchBarDestroy);

      // Initialize the search bar size
      $('body').trigger('cds.search.bar.resize');

      // Check if the searchbar has been resized
      $(window).on('resize', function() {
        $('body').trigger('cds.search.bar.resize');
      });

      $('.cds-remove-search-to-collection').on('click', function(ev) {
        ev.preventDefault();
        $searchForm.find('[name=cc]').val('');
        $(this).parent().fadeOut('slow').remove();
        $('body').trigger('cds.search.bar.resize');
      });
    });
});
