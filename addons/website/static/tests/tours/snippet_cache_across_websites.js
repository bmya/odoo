/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

wTourUtils.registerWebsitePreviewTour('snippet_cache_across_websites', {
    edition: true,
    test: true,
    url: '/@/'
}, () => [
    {
        content: "Check that the custom snippet is displayed",
        trigger: '#snippet_custom_body span:contains("custom_snippet_test")',
        run: () => null,
    },
    // There's no need to save, but canceling might or might not show a popup...
    ...wTourUtils.clickOnSave(),
    ...wTourUtils.switchWebsite(2, 'My Website 2'),
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        trigger: '#oe_snippets:not(:has(#snippet_custom_body span:contains("custom_snippet_test")))',
    },
    {
        content: "Check that the custom snippet is not here",
        trigger: '#oe_snippets:not(:has(#snippet_custom))',
        run: () => null,
    },
]);
