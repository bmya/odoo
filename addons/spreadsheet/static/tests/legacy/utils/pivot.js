/** @odoo-module */

import { PivotArchParser } from "@web/views/pivot/pivot_arch_parser";
import { nextTick } from "@web/../tests/helpers/utils";

import { OdooPivot } from "@spreadsheet/pivot/odoo_pivot";
import { getBasicServerData, getBasicPivotArch } from "@spreadsheet/../tests/legacy/utils/data";
import { createModelWithDataSource } from "@spreadsheet/../tests/legacy/utils/model";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import { helpers } from "@odoo/o-spreadsheet";
const { parseDimension, isDateField } = helpers;

/**
 * @typedef {import("@spreadsheet").OdooSpreadsheetModel} OdooSpreadsheetModel
 * @typedef {import("@spreadsheet").Zone} Zone
 */

function addEmptyGranularity(dimensions, fields) {
    return dimensions.map((dimension) => {
        if (dimension.name !== "id" && isDateField(fields[dimension.name])) {
            return {
                granularity: "month",
                ...dimension,
            };
        }
        return dimension;
    });
}

/**
 * @param {OdooSpreadsheetModel} model
 * @param {string} pivotId
 * @param {object} params
 * @param {string} [params.arch]
 * @param {string} [params.resModel]
 * @param {object} [params.serverData]
 * @param {string} [params.sheetId]
 * @param {[number, number]} [params.anchor]
 */
export async function insertPivotInSpreadsheet(model, pivotId, params) {
    const archInfo = new PivotArchParser().parse(params.arch || getBasicPivotArch());
    const serverData = params.serverData || getBasicServerData();
    const resModel = params.resModel || "partner";
    const pivot = {
        type: "ODOO",
        sortedColumn: null,
        domain: [],
        context: {},
        measures: archInfo.activeMeasures.map((measure) => ({
            name: measure,
            aggregator: serverData.models[resModel].fields[measure]?.aggregator,
        })),
        model: resModel,
        columns: addEmptyGranularity(
            archInfo.colGroupBys.map(parseDimension),
            serverData.models[resModel].fields
        ),
        rows: addEmptyGranularity(
            archInfo.rowGroupBys.map(parseDimension),
            serverData.models[resModel].fields
        ),
        name: "Partner Pivot",
    };
    model.dispatch("ADD_PIVOT", {
        pivotId,
        pivot,
    });
    const ds = model.getters.getPivot(pivotId);
    if (!(ds instanceof OdooPivot)) {
        throw new Error("The pivot data source is not an OdooPivot");
    }
    await ds.load();
    const { cols, rows, measures, fieldsType } = ds.getTableStructure().export();
    const table = {
        cols,
        rows,
        measures,
        fieldsType,
    };
    const [col, row] = params.anchor || [0, 0];
    model.dispatch("INSERT_PIVOT", {
        pivotId,
        sheetId: params.sheetId || model.getters.getActiveSheetId(),
        col,
        row,
        table,
    });
    await nextTick();
}

/**
 * @param {object} params
 * @param {string} [params.arch]
 * @param {object} [params.serverData]
 * @param {function} [params.mockRPC]
 * @returns {Promise<{ model: OdooSpreadsheetModel, env: object, pivotId: string}>}
 */
export async function createSpreadsheetWithPivot(params = {}) {
    const serverData = params.serverData || getBasicServerData();
    const model = await createModelWithDataSource({
        mockRPC: params.mockRPC,
        serverData: params.serverData,
    });
    const arch = params.arch || serverData.views["partner,false,pivot"];
    const pivotId = "PIVOT#1";
    await insertPivotInSpreadsheet(model, pivotId, { arch });
    const env = model.config.custom.env;
    env.model = model;
    await waitForDataLoaded(model);
    return { model, env, pivotId };
}

/**
 * Return the zone that contains all the cells of the given data source
 *
 * TODO: Un-duplicate this once this or #50623 is merged
 *
 * @param model
 * @param {"pivot" | "list"} dataSourceType
 * @param {string} id
 * @returns {Zone}
 */
export function getZoneOfInsertedDataSource(model, dataSourceType, id) {
    const sheetId = model.getters.getActiveSheetId();
    const cells = model.getters.getCells(sheetId);
    const positions = Object.keys(cells).map(model.getters.getCellPosition);

    let top = 0;
    let left = 0;
    let bottom = 0;
    let right = 0;
    for (const position of positions) {
        const cellDataSourceId =
            dataSourceType === "pivot"
                ? model.getters.getPivotIdFromPosition({ sheetId, ...position })
                : model.getters.getListIdFromPosition({ sheetId, ...position });
        if (id !== cellDataSourceId) {
            continue;
        }
        top = Math.min(top, position.row);
        left = Math.min(left, position.col);
        bottom = Math.max(bottom, position.row);
        right = Math.max(right, position.col);
    }
    return { top, bottom, left, right };
}
