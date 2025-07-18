import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add('snippets_mailing_menu_toolbar_mobile', {
    url: '/odoo',
    steps: () => [
    stepUtils.showAppsMenuItem(), {
        content: "Select the 'Email Marketing' app.",
        trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
        run: "click",
    },
    {
        isActive: ["mobile"],
        content: "Click on the create button to create a new mailing.",
        trigger: 'button.o_list_button_add',
        run: "click",
    },
    {
        isActive: ["mobile"],
        content: "Check templates available in theme selector",
        trigger: ':iframe .o_mail_theme_selector_new',
        run: function () {
            if (this.anchor.querySelector("#empty")) {
                console.error('The empty template should not be visible on mobile.');
            }
        },
    },
    {
        isActive: ["mobile"],
        content: "Make sure the toolbar isn't floating",
        trigger: ':iframe',
        run: function () {
            const iframeDocument = this.anchor.contentDocument;
            if (iframeDocument.querySelector('#toolbar.oe-floating')) {
                console.error('There should not be a floating toolbar in the iframe');
            }
        },
    },
    {
        isActive: ["mobile"],
        content: "Click on the 'Start From Scratch' template.",
        trigger: ':iframe #default',
        run: "click",
    },
    {
        isActive: ["mobile"],
        content: "Select an editable element",
        trigger: ':iframe .s_text_block',
        run: "click",
    },
    {
        isActive: ["mobile"],
        content: "Make sure the snippets menu is hidden",
        trigger: ':iframe',
        run: function () {
            const iframeDocument = this.anchor.contentDocument;
            if (!iframeDocument.querySelector('#oe_snippets.d-none')) {
                console.error('The snippet menu should be hidden');
            }
        },
    },
    {
        isActive: ["mobile"],
        content: "Make sure the toolbar is there",
        trigger: ':iframe #toolbar.oe-floating',
    },
    ...stepUtils.discardForm().map(command => ({...command, isActive: ["mobile"]})),
    ]
});
