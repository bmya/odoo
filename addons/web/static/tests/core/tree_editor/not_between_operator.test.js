import { describe, expect, test } from "@odoo/hoot";

import { makeMockEnv } from "@web/../tests/web_test_helpers";

import {
    applyTransformations,
    condition,
    connector,
    expression,
    FULL_VIRTUAL_OPERATORS_ELIMINATION,
    FULL_VIRTUAL_OPERATORS_INTRODUCTION,
} from "@web/core/tree_editor/condition_tree";

describe.current.tags("headless");

const options = {
    getFieldDef: (name) => {
        if (name === "m2o") {
            return { type: "many2one" };
        }
        if (name === "m2o.datetime_2" || name === "datetime_1") {
            return { type: "datetime" };
        }
        if (name === "m2o.int_2" || name === "int_1") {
            return { type: "integer" };
        }
        return null;
    },
};

test("not_between operator: introduction/elimination", async () => {
    await makeMockEnv();
    const toTest = [
        {
            tree_py: connector("|", [condition("int_1", "<", 1), condition("int_1", ">", 2)]),
            tree: condition("int_1", "not_between", [1, 2]),
        },
        {
            tree_py: connector("|", [condition("int_1", "<", 1), condition("int_1", ">", 2)], true),
            tree: condition("int_1", "not_between", [1, 2], true),
        },
        {
            tree_py: connector("|", [
                condition("m2o.int_2", "<", 1),
                condition("m2o.int_2", ">", 2),
            ]),
            tree: connector("|", [condition("m2o.int_2", "<", 1), condition("m2o.int_2", ">", 2)]),
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("|", [condition("int_2", "<", 1), condition("int_2", ">", 2)])
            ),
            tree: condition("m2o.int_2", "not_between", [1, 2]),
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("|", [condition("int_2", "<", 1), condition("int_2", ">", 2)]),
                true
            ),
            tree: condition("m2o", "any", condition("int_2", "not_between", [1, 2]), true),
        },

        {
            tree_py: connector("|", [
                condition("datetime_1", "<", 1),
                condition("datetime_1", ">", 2),
            ]),
            tree: condition("datetime_1", "not_between", [1, 2]),
        },
        {
            tree_py: connector(
                "|",
                [condition("datetime_1", "<", 1), condition("datetime_1", ">", 2)],
                true
            ),
            tree: condition("datetime_1", "not_between", [1, 2], true),
        },
        {
            tree_py: connector("|", [
                condition("m2o.datetime_2", "<", 1),
                condition("m2o.datetime_2", ">", 2),
            ]),
            tree: connector("|", [
                condition("m2o.datetime_2", "<", 1),
                condition("m2o.datetime_2", ">", 2),
            ]),
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("|", [condition("datetime_2", "<", 1), condition("datetime_2", ">", 2)])
            ),
            tree: condition("m2o.datetime_2", "not_between", [1, 2]),
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("|", [condition("datetime_2", "<", 1), condition("datetime_2", ">", 2)]),
                true
            ),
            tree: condition("m2o", "any", condition("datetime_2", "not_between", [1, 2]), true),
        },

        {
            tree_py: connector("|", [
                condition(expression("path"), "<", 1),
                condition(expression("path"), ">", 2),
            ]),
            tree: connector("|", [
                condition(expression("path"), "<", 1),
                condition(expression("path"), ">", 2),
            ]),
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("|", [
                    condition(expression("path"), "<", 1),
                    condition(expression("path"), ">", 2),
                ])
            ),
            tree: condition(
                "m2o",
                "any",
                connector("|", [
                    condition(expression("path"), "<", 1),
                    condition(expression("path"), ">", 2),
                ])
            ),
        },
    ];
    for (const { tree_py, tree } of toTest) {
        expect(applyTransformations(FULL_VIRTUAL_OPERATORS_INTRODUCTION, tree_py, options)).toEqual(
            tree
        );
        expect(applyTransformations(FULL_VIRTUAL_OPERATORS_ELIMINATION, tree)).toEqual(tree_py);
    }
});
