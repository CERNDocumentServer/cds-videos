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

"use strict";

define([
  'js/record_tools',
  'jasmine-jquery',
], function(record_tools, jasmineJQuery) {
  "use strict";

	describe('The "expandContent" function...', function() {

		describe('...as far as the text is concerned...', function() {
			
			beforeEach(function() {
				jasmine.getFixtures().fixturesPath = '/jasmine/spec/cds.base/fixtures/';
				$('body').append(readFixtures('read_more.html'));
				record_tools.expandContent();
		  	});

		  	afterEach(function() {
				$('#textArea').remove();
			});

			it('should allow only 60 words to be visible, at first.', function() {
				var content = ($('#textArea')).text();
		        var text = content.split(" ");
		        var len = text.length;

		    	expect(len).toBe(60+2);
			});

			it('should allow all the words (10000) to be visible, after click.', function()
			{
				var link = $('.record-brief-view-more-link');
				link.click();
				var content = ($('#textArea')).text();
		        var text = content.split(" ");
		        var len = text.length;

		    	expect(len).toBe(10000+1);
			});

			it('should allow only 60 words to be visible, after second click.', function() {
				var link = $('.record-brief-view-more-link');
				link.click();
				link.click();

				var content = ($('#textArea')).text();
		        var text = content.split(" ");
		        var len = text.length;

		    	expect(len).toBe(60+2);
			});
		});

		describe('...as far as the state of the text is concerned...', function() {

			beforeEach(function() {
				jasmine.getFixtures().fixturesPath = '/jasmine/spec/cds.base/fixtures/';
				$('body').append(readFixtures('read_more.html'));
				record_tools.expandContent();
		  	});

		  	afterEach(function() {
				$('#textArea').remove();
			});

		  	it('should begin with state "shortState".', function() {
				var state = ($('#textArea')).data("state");

				expect(state).toBe("shortState");
			});


			it('should change the state of the text to "fullState" after click.', function() {
				var link = $('.record-brief-view-more-link');
				link.click();

				var state = ($('#textArea')).data("state");

				expect(state).toBe("fullState");
			});

			it('should change the state of the text to "shortState" again, after second click.', function() {
				var link = $('.record-brief-view-more-link');
				link.click();
				link.click();

				var state = ($('#textArea')).data("state");

				expect(state).toBe("shortState");
			});

		});

		describe('...as far as the link is concerned...', function() {

			beforeEach(function() {
				jasmine.getFixtures().fixturesPath = '/jasmine/spec/cds.base/fixtures/';
				$('body').append(readFixtures('read_more.html'));
				record_tools.expandContent();
		  	});

		  	afterEach(function() {
				$('#textArea').remove();
			});

			it('should create a "read more" link.', function() {
				var link = $('.record-brief-view-more-link');
				expect(link).toExist();
				expect(link.text()).toBe("(read more)");
			});

			

			it('should allow the "read more" link to be triggered.', function() {
				var spyEvent = spyOnEvent('.record-brief-view-more-link', 'click');
				$('.record-brief-view-more-link').click();
				expect('click').toHaveBeenTriggeredOn('.record-brief-view-more-link');
				expect(spyEvent).toHaveBeenTriggered();
			});


			it('should convert the "read more" link into a "read less" link, on click.', function() {
				var link = $('.record-brief-view-more-link');
				link.click();

				expect(link.text()).toBe("(read less)");
			});

			it('should convert the "read less" link into a "read more" link, on second click.', function() {
				var link = $('.record-brief-view-more-link');
				link.click();
				link.click();

				expect(link.text()).toBe("(read more)");
			});			
		});
		
	});
});



 