import { _t } from "@web/core/l10n/translation";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";
const formatters = registry.category("formatters");

export class BadgeField extends Component {
    static template = "web.BadgeField";
    static props = {
        ...standardFieldProps,
        decorations: { type: Object, optional: true },
        colorField: { type: String, optional: true },
    };
    static defaultProps = {
        decorations: {},
    };

    get formattedValue() {
        const formatter = formatters.get(this.props.record.fields[this.props.name].type);
        return formatter(this.props.record.data[this.props.name], {
            selection: this.props.record.fields[this.props.name].selection,
        });
    }

    get badgeClass() {
        if (this.props.colorField) {
            return `o_badge_color_${this.props.record.data[this.props.colorField]}`;
        }
        const evalContext = this.props.record.evalContextWithVirtualIds;
        for (const decorationName in this.props.decorations) {
            if (evaluateBooleanExpr(this.props.decorations[decorationName], evalContext)) {
                // fallback case for text-bg-muted
                if (decorationName === "muted") {
                    return "text-bg-300";
                }
                return `text-bg-${decorationName}`;
            }
        }
        return "text-bg-300";
    }
}

export const badgeField = {
    component: BadgeField,
    displayName: _t("Badge"),
    supportedTypes: ["selection", "many2one", "char"],
    supportedOptions: [
        {
            label: _t("Color field"),
            name: "color_field",
            type: "field",
            availableTypes: ["integer"],
            help: _t("Set an integer field to use colors with the badge."),
        },
    ],
    extractProps: ({ decorations, options }) => {
        return {
            decorations,
            colorField: options.color_field,
        };
    },
};

registry.category("fields").add("badge", badgeField);
