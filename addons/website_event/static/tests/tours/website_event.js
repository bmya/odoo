import {
    insertSnippet,
    registerWebsitePreviewTour,
    clickOnEditAndWaitEditMode,
    clickOnSave,
} from '@website/js/tours/tour_utils';

function websiteCreateEventTourSteps() {
    return [
        {
            content: "Click here to add new content to your website.",
            trigger: ".o_menu_systray .o_new_content_container > a",
            tooltipPosition: "bottom",
            run: "click",
        }, {
            trigger: "a[data-module-xml-id='base.module_website_event']",
            content: "Click here to create a new event.",
            tooltipPosition: "bottom",
            run: "click",
        }, {
            trigger: '.modal-dialog .o_field_widget[name="name"] .o_input',
            content: "Create a name for your new event and click Continue. e.g: Technical Training",
            run: "edit Technical Training",
            tooltipPosition: "left",
        }, {
            trigger: ".modal-dialog div[name=date_begin]",
            content: "Open date range picker. Pick a Start date for your event",
            run() {
                const el1 = document.querySelector("input[data-field='date_begin']");
                el1.value = "09/30/2020 08:00:00";
                el1.dispatchEvent(new Event("change", {bubbles: true, cancelable: true}));
                const el2 = document.querySelector("input[data-field='date_end']");
                el2.value = "10/02/2020 23:00:00";
                el2.dispatchEvent(new Event("change", {bubbles: true, cancelable: true}));
                el1.click();
            }
        },
        {
            trigger: '.modal-dialog div[name="event_ticket_ids"] .o_field_x2many_list_row_add a:contains("Add a line")',
            content: "Click here to add a ticket",
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".modal-dialog input[type=text]:not(:value(''))",
        },
        {
            trigger: '.modal-footer button.btn-primary',
            content: "Click Continue to create the event.",
            tooltipPosition: "right",
            run: "click",
        },
        ...insertSnippet({
            id: "s_image_text",
            name: "Image - Text",
            groupName: "Content",
        }),
        ...clickOnSave(),
        {
            trigger: ".o_menu_systray_item.o_website_publish_container a",
            content: "Click to publish your event.",
            tooltipPosition: "top",
            run: "click",
        }, {
            trigger: ".o_website_edit_in_backend > a",
            content: "Click here to customize your event further.",
            tooltipPosition: "bottom",
        },
    ];
}

function websiteEditEventTourSteps() {
    return [
        {
            content: "Redirect to Event Page",
            trigger: ":iframe a[title='Back to All Events']",
            run: "click",
        },
        {
            content: "Wait for events list to load",
            trigger: ":iframe .opt_events_list_columns",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "edit the short description of the event",
            trigger: ":iframe .opt_events_list_columns small",
            run: function () {
                this.anchor.innerHTML = "new short description";
            }
        },
        ...clickOnSave(),
        {
            content: "is short description updated?",
            trigger: ":iframe .opt_events_list_columns small:contains('new short description')",
        },
    ];
}

registerWebsitePreviewTour(
    "website_event_tour", {
        url: "/",
    },
    () => [...websiteCreateEventTourSteps(), ...websiteEditEventTourSteps()]
);
