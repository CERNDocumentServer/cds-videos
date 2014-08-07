/*
 * This file is part of Invenio.
 * Copyright (C) 2014 CERN.
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

({
    baseUrl: '',
    preserveLicenseComments: false,
    optimize: 'uglify2',
    uglify2: {
        output: {
            beautify: false,
            comments: false
        },
        compress: {
            drop_console: true
        },
        warnings: true,
        mangle: false
    },
    paths: {
        // Invenio
        jquery: 'empty:',
        'jquery-ui': 'vendors/jquery-ui/jquery-ui',  // to be removed
        'ui': 'vendors/jquery-ui/ui',
        'jqueryui-timepicker': 'vendors/jqueryui-timepicker-addon/dist',
        'jquery-form': 'vendors/jquery-form/jquery.form',
        hgn: 'vendors/requirejs-hogan-plugin/hgn',
        hogan: 'vendors/hogan/web/builds/3.0.2/hogan-3.0.2.amd',
        text: 'vendors/requirejs-hogan-plugin/text'
        // CDS
        react: 'vendors/jsx-requirejs-plugin/js/react-with-addons-0.10.0',
        jsx: 'vendors/jsx-requirejs-plugin/js/jsx',
        JSXTransformer: 'vendors/jsx-requirejs-plugin/js/JSXTransformer-0.10.0',
        json: 'vendors/requirejs-plugins/src/json',
        backbone: 'vendors/backbone/backbone',
        'backbone.localStorage': 'vendors/backbone.localstorage/backbone.localStorage',
        underscore: 'vendors/underscore/underscore',
    },
    shim: {
        // Invenio
        jquery: { exports: '$' },
        'jqueryui-timepicker/jqueryui-sliderAccess': {deps: ['jquery']},
        'jqueryui-timepicker/jqueryui-timepicker-addon': {deps: ['jquery', 'ui/slider']},
        'jqueryui-timepicker/i18n/jquery-ui-timepicker-addon-i18n': {deps: ['jqueryui-timepicker/jquery-ui-timepicker-addon']},
        // CDS
        react: { exports: 'React' },
        backbone: { deps: ['underscore', 'jquery'], exports: 'Backbone'},
        'backbone.localstorage': { deps: ['backbone'], exports: 'Backbone.LocalStorage' },
        underscore: { exports: '_' }
    },
    onBuildWrite: function (moduleName, path, singleContents) {
        // Dropping jsx related files
        if (['jsx', 'JSXTransformer'].indexOf(moduleName) >= 0) {
            return '';
        }
        return singleContents.replace(/jsx!/g, '');
    }
})
