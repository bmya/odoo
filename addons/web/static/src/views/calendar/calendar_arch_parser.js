import { browser } from "@web/core/browser/browser";
import { evaluateExpr } from "@web/core/py_js/py";
import { exprToBoolean } from "@web/core/utils/strings";
import { visitXML } from "@web/core/utils/xml";
import { Field } from "@web/views/fields/field";

const FIELD_ATTRIBUTE_NAMES = [
    "date_start",
    "date_delay",
    "date_stop",
    "all_day",
    "create_name_field",
    "color",
];
const SCALES = ["day", "week", "month", "year"];

export class CalendarParseArchError extends Error {}

export class CalendarArchParser {
    parse(xmlDoc, models, modelName) {
        const fields = models[modelName].fields;
        const fieldNames = new Set(fields.display_name ? ["display_name"] : []);
        const fieldMapping = { date_start: "date_start" };
        let jsClass = null;
        let eventLimit = 5;
        let scales = [...SCALES];
        const sessionScale = browser.sessionStorage.getItem("calendar-scale"); // FIXME: move
        let scale = sessionScale || "week";
        let canCreate = true;
        let canDelete = true;
        let canEdit = true;
        let aggregate;
        let quickCreate = true;
        let quickCreateViewId = null;
        const multiCreateView = xmlDoc.getAttribute("multi_create_view");
        let hasEditDialog = false;
        let showUnusualDays = false;
        let isDateHidden = false;
        let isTimeHidden = false;
        let formViewId = false;
        let showDatePicker = true;
        let monthOverflow = true;
        const popoverFieldNodes = {};
        const filtersInfo = {};

        visitXML(xmlDoc, (node) => {
            switch (node.tagName) {
                case "calendar": {
                    if (!node.hasAttribute("date_start")) {
                        throw new CalendarParseArchError(
                            `Calendar view has not defined "date_start" attribute.`
                        );
                    }

                    jsClass = node.getAttribute("js_class");

                    for (const fieldAttrName of FIELD_ATTRIBUTE_NAMES) {
                        if (node.hasAttribute(fieldAttrName)) {
                            const fieldName = node.getAttribute(fieldAttrName);
                            fieldNames.add(fieldName);
                            fieldMapping[fieldAttrName] = fieldName;
                        }
                    }
                    if (node.hasAttribute("aggregate")) {
                        aggregate = node.getAttribute("aggregate");
                        fieldNames.add(aggregate.split(":")[0]);
                    }

                    if (node.hasAttribute("event_limit")) {
                        eventLimit = evaluateExpr(node.getAttribute("event_limit"));
                        if (!Number.isInteger(eventLimit)) {
                            throw new CalendarParseArchError(
                                `Calendar view's event limit should be a number`
                            );
                        }
                    }
                    if (node.hasAttribute("scales")) {
                        const scalesAttr = node.getAttribute("scales");
                        scales = scalesAttr.split(",").filter((scale) => SCALES.includes(scale));
                    }
                    if (node.hasAttribute("mode")) {
                        scale = node.getAttribute("mode");
                        if (!scales.includes(scale)) {
                            throw new CalendarParseArchError(
                                `Calendar view cannot display mode: ${scale}`
                            );
                        }
                    }
                    if (node.hasAttribute("create")) {
                        canCreate = exprToBoolean(node.getAttribute("create"), true);
                    }
                    if (node.hasAttribute("delete")) {
                        canDelete = exprToBoolean(node.getAttribute("delete"), true);
                    }
                    if (node.hasAttribute("edit")) {
                        canEdit = exprToBoolean(node.getAttribute("edit"), true);
                    }
                    if (node.hasAttribute("quick_create")) {
                        quickCreate = exprToBoolean(node.getAttribute("quick_create"), true);
                        if (quickCreate && node.hasAttribute("quick_create_view_id")) {
                            quickCreateViewId = parseInt(
                                node.getAttribute("quick_create_view_id"),
                                10
                            );
                        }
                    }
                    if (node.hasAttribute("event_open_popup")) {
                        hasEditDialog = exprToBoolean(node.getAttribute("event_open_popup"));
                    }
                    if (node.hasAttribute("show_unusual_days")) {
                        showUnusualDays = exprToBoolean(node.getAttribute("show_unusual_days"));
                    }
                    if (node.hasAttribute("hide_date")) {
                        isDateHidden = exprToBoolean(node.getAttribute("hide_date"));
                    }
                    if (node.hasAttribute("hide_time")) {
                        isTimeHidden = exprToBoolean(node.getAttribute("hide_time"));
                    }
                    if (node.hasAttribute("form_view_id")) {
                        formViewId = parseInt(node.getAttribute("form_view_id"), 10);
                    }
                    if (node.hasAttribute("show_date_picker")) {
                        showDatePicker = exprToBoolean(node.getAttribute("show_date_picker"));
                    }
                    if (node.hasAttribute("month_overflow")) {
                        monthOverflow = exprToBoolean(node.getAttribute("month_overflow"));
                    }

                    break;
                }
                case "field": {
                    const fieldName = node.getAttribute("name");
                    fieldNames.add(fieldName);

                    const fieldInfo = Field.parseFieldNode(
                        node,
                        models,
                        modelName,
                        "calendar",
                        jsClass
                    );
                    popoverFieldNodes[fieldName] = fieldInfo;

                    const field = fields[fieldName];
                    if (!node.hasAttribute("invisible") || node.hasAttribute("filters")) {
                        let filterInfo = null;
                        if (
                            node.hasAttribute("avatar_field") ||
                            node.hasAttribute("write_model") ||
                            node.hasAttribute("write_field") ||
                            node.hasAttribute("color") ||
                            node.hasAttribute("filters")
                        ) {
                            filtersInfo[fieldName] = filtersInfo[fieldName] || {
                                avatarFieldName: null,
                                colorFieldName: null,
                                fieldName,
                                filterFieldName: null,
                                label: field.string,
                                resModel: field.relation,
                                writeFieldName: null,
                                writeResModel: null,
                                context: fieldInfo.context || "{}",
                            };
                            filterInfo = filtersInfo[fieldName];
                        }
                        if (node.hasAttribute("filter_field")) {
                            filterInfo.filterFieldName = node.getAttribute("filter_field");
                        }
                        if (node.hasAttribute("avatar_field")) {
                            filterInfo.avatarFieldName = node.getAttribute("avatar_field");
                        }
                        if (node.hasAttribute("write_model")) {
                            filterInfo.writeResModel = node.getAttribute("write_model");
                        }
                        if (node.hasAttribute("write_field")) {
                            filterInfo.writeFieldName = node.getAttribute("write_field");
                        }
                        if (node.hasAttribute("filters") && node.hasAttribute("color")) {
                            filterInfo.colorFieldName = node.getAttribute("color");
                        }
                    }

                    break;
                }
            }
        });

        return {
            aggregate,
            canCreate,
            canDelete,
            canEdit,
            eventLimit,
            fieldMapping,
            fieldNames: [...fieldNames],
            filtersInfo,
            formViewId,
            hasEditDialog,
            multiCreateView,
            quickCreate,
            quickCreateViewId,
            isDateHidden,
            isTimeHidden,
            monthOverflow,
            popoverFieldNodes,
            scale,
            scales,
            showUnusualDays,
            showDatePicker,
        };
    }
}
