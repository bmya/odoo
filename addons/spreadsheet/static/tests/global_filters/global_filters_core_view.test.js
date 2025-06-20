/** @ts-check */
import { describe, expect, test } from "@odoo/hoot";

import { Model } from "@odoo/o-spreadsheet";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import {
    addGlobalFilterWithoutReload,
    setGlobalFilterValueWithoutReload,
} from "@spreadsheet/../tests/helpers/commands";
import { RELATIVE_PERIODS } from "@spreadsheet/global_filters/helpers";

describe.current.tags("headless");
defineSpreadsheetModels();

test("Value of text filter", () => {
    const model = new Model();
    addGlobalFilterWithoutReload(model, {
        id: "1",
        type: "text",
        label: "Text Filter",
    });

    let result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: "test",
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "2",
        type: "text",
        label: "Default value is an array",
        defaultValue: ["default value"],
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: 5,
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: false,
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);
});

test("Value of date filter", () => {
    const model = new Model();
    addGlobalFilterWithoutReload(model, {
        id: "1",
        type: "date",
        label: "Date Filter",
    });

    let result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: "test",
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "year" },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "year", year: 2022 },
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: 5,
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: false,
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "month", month: 5 },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "month", year: 2020 },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "month", month: 5, year: 2016 },
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "quarter", year: 2020 },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "quarter", quarter: 3 },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "quarter", quarter: 3, year: 2016 },
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "year" },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "year", year: 2016 },
    });
    expect(result.isSuccessful).toBe(true);

    for (const period of Object.keys(RELATIVE_PERIODS)) {
        result = setGlobalFilterValueWithoutReload(model, {
            id: "1",
            value: { type: "relative", period },
        });
        expect(result.isSuccessful).toBe(true);
    }
});

test("Value of relation filter", () => {
    const model = new Model();
    addGlobalFilterWithoutReload(model, {
        id: "1",
        type: "relation",
        label: "Relation Filter",
    });

    let result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: "test",
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: [1, 2, 3],
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: 5,
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "5",
        type: "relation",
        label: "Default value cannot be a boolean",
        defaultValue: false,
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: "current_user",
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: ["1"],
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);
});

test("Value of boolean filter", () => {
    const model = new Model();
    addGlobalFilterWithoutReload(model, {
        id: "1",
        type: "boolean",
        label: "Boolean filter",
    });

    let result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: "test",
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: [true, false],
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: 5,
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: false,
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);
});
