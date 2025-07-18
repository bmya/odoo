import { useDebugCategory } from "@web/core/debug/debug_context";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { KeepLast } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { deepCopy, pick } from "@web/core/utils/objects";
import { nbsp } from "@web/core/utils/strings";
import { parseXML } from "@web/core/utils/xml";
import { extractLayoutComponents } from "@web/search/layout";
import { WithSearch } from "@web/search/with_search/with_search";
import { useActionLinks } from "@web/views/view_hook";
import { computeViewClassName } from "./utils";
import { loadBundle } from "@web/core/assets";
import { cookie } from "@web/core/browser/cookie";
import {
    Component,
    markRaw,
    onWillUpdateProps,
    onWillStart,
    toRaw,
    useSubEnv,
    reactive,
} from "@odoo/owl";
import { session } from "@web/session";

/**
 * @typedef Config
 * @property {number | false} actionId
 * @property {string | false} actionType
 * @property {() => []} breadcrumbs
 * @property {() => string} getDisplayName
 * @property {(string) => any} setDisplayName
 * @property {() => Record<string, any>} getPagerProps
 * @property {Record<string, any>[]} viewSwitcherEntry
 * @property {typeof Component} Banner
 *
 * @typedef {import("@web/core/context").Context} Context
 * @typedef {import("@web/env").OdooEnv} OdooEnv
 * @typedef {import("@web/search/utils/order_by").OrderTerm} OrderTerm
 *
 * @typedef ViewProps
 * @property {string} resModel
 * @property {ViewType} type
 *
 * @property {string} [arch] if given, fields must be given too /\ no post processing is done (evaluation of "groups" attribute,...)
 * @property {Record<string, any>} [fields] if given, arch must be given too
 * @property {number|false} [viewId]
 * @property {Record<string, any>} [actionMenus]
 * @property {boolean} [loadActionMenus=false]
 *
 * @property {string} [searchViewArch] if given, searchViewFields must be given too
 * @property {Record<string, any>} [searchViewFields] if given, searchViewArch must be given too
 * @property {number|false} [searchViewId]
 * @property {Record<string, any>[]} [irFilters]
 * @property {boolean} [loadIrFilters=false]
 *
 * @property {Record<string, any>} [comparison]
 * @property {Context} [context={}]
 * @property {DomainRepr} [domain]
 * @property {string[]} [groupBy]
 * @property {OrderTerm[]} [orderBy]
 *
 * @property {boolean} [useSampleModel]
 * @property {string} [noContentHelp]
 *
 * @property {Record<string, any>} [display={}] to rework
 *
 * --- Manipulated by withSearch ---
 * @property {boolean} [activateFavorite]
 * @property {Record<string, any>[]} [dynamicFilters]
 * @property {boolean} [hideCustomGroupBy]
 * @property {string[]} [searchMenuTypes]
 * @property {Record<string, any>} [globalState]
 *
 * @typedef {"activity"
 *  | "calendar"
 *  | "cohort"
 *  | "form"
 *  | "gantt"
 *  | "graph"
 *  | "grid"
 *  | "hierarchy"
 *  | "kanban"
 *  | "list"
 *  | "map"
 *  | "pivot"
 *  | "search"
 * } ViewType
 */

const viewRegistry = registry.category("views");

viewRegistry.addValidation({
    type: { validate: (t) => t in session.view_info },
    Controller: { validate: (c) => c.prototype instanceof Component },
    "*": true,
});

/**
 * Returns the default config to use if no config, or an incomplete config has
 * been provided in the env, which can happen with standalone views.
 * @returns {Config}
 */
export function getDefaultConfig() {
    let displayName;
    const config = {
        actionId: false,
        actionType: false,
        cache: true,
        embeddedActions: [],
        currentEmbeddedActionId: false,
        parentActionId: false,
        breadcrumbs: reactive([
            {
                get name() {
                    return displayName;
                },
            },
        ]),
        disableSearchBarAutofocus: false,
        getDisplayName: () => displayName,
        historyBack: () => {},
        pagerProps: {},
        setDisplayName: (newDisplayName) => {
            displayName = newDisplayName;
            // This is a hack to force the reactivity when a new displayName is set
            config.breadcrumbs.push(undefined);
            config.breadcrumbs.pop();
        },
        viewSwitcherEntries: [],
        views: [],
    };
    return config;
}

export class ViewNotFoundError extends Error {}

const CALLBACK_RECORDER_NAMES = [
    "__beforeLeave__",
    "__getGlobalState__",
    "__getLocalState__",
    "__getContext__",
    "__getOrderBy__",
];

const STANDARD_PROPS = [
    "resModel",
    "type",
    "jsClass",

    "arch",
    "fields",
    "relatedModels",
    "viewId",
    "views",
    "actionMenus",
    "loadActionMenus",

    "searchViewArch",
    "searchViewFields",
    "searchViewId",
    "irFilters",
    "loadIrFilters",

    "context",
    "domain",
    "groupBy",
    "orderBy",

    "useSampleModel",
    "noContentHelp",
    "className",

    "display",
    "globalState",

    "activateFavorite",
    "dynamicFilters",
    "hideCustomGroupBy",
    "searchMenuTypes",

    ...CALLBACK_RECORDER_NAMES,

    // LEGACY: remove this later (clean when mappings old state <-> new state are established)
    "searchPanel",
    "searchModel",
];

const ACTIONS = ["create", "delete", "edit", "group_create", "group_delete", "group_edit"];

/** @extends {Component<ViewProps, import("@web/env").OdooEnv>} */
export class View extends Component {
    static _download = async function () {};
    static template = "web.View";
    static components = { WithSearch };
    static searchMenuTypes = ["filter", "groupBy", "favorite"];
    static canOrderByCount = false;
    static defaultProps = {
        display: {},
        context: {},
        loadActionMenus: false,
        loadIrFilters: false,
        className: "",
    };
    static props = {
        "*": true,
    };

    setup() {
        const { arch, fields, resModel, searchViewArch, searchViewFields, type } = this.props;
        if (!resModel) {
            throw Error(`View props should have a "resModel" key`);
        }
        if (!type) {
            throw Error(`View props should have a "type" key`);
        }
        if ((arch && !fields) || (!arch && fields)) {
            throw new Error(`"arch" and "fields" props must be given together`);
        }
        if ((searchViewArch && !searchViewFields) || (!searchViewArch && searchViewFields)) {
            throw new Error(`"searchViewArch" and "searchViewFields" props must be given together`);
        }

        this.viewService = useService("view");
        this.withSearchProps = null;

        useSubEnv({
            keepLast: new KeepLast(),
            config: {
                ...getDefaultConfig(),
                ...this.env.config,
            },
            ...Object.fromEntries(
                CALLBACK_RECORDER_NAMES.map((name) => [name, this.props[name] || null])
            ),
        });

        this.handleActionLinks = useActionLinks({ resModel });

        onWillStart(() => this.loadView(this.props));
        onWillUpdateProps((nextProps) => this.onWillUpdateProps(nextProps));

        useDebugCategory("view", { component: this });
    }

    /**
     * @param {ViewProps} props
     */
    async loadView(props) {
        const type = props.type;

        if (!session.view_info[type]) {
            throw new Error(`Invalid view type: ${type}`);
        }

        // determine views for which descriptions should be obtained
        let { viewId, searchViewId } = props;

        const views = deepCopy(props.views || this.env.config.views);
        const view = views.find((v) => v[1] === type) || [];
        if (view.length) {
            view[0] = viewId !== undefined ? viewId : view[0];
            viewId = view[0];
        } else {
            view.push(viewId || false, type);
            views.push(view); // viewId will remain undefined if not specified and loadView=false
        }

        const searchView = views.find((v) => v[1] === "search");
        if (searchView) {
            searchView[0] = searchViewId !== undefined ? searchViewId : searchView[0];
            searchViewId = searchView[0];
        } else if (searchViewId !== undefined) {
            views.push([searchViewId, "search"]);
        }
        // searchViewId will remains undefined if loadSearchView=false

        // prepare view description
        const { context, resModel, loadActionMenus, loadIrFilters } = props;
        let {
            arch,
            fields,
            relatedModels,
            searchViewArch,
            searchViewFields,
            irFilters,
            actionMenus,
        } = props;

        const loadView = !arch || (!actionMenus && loadActionMenus);
        const loadSearchView =
            (searchViewId !== undefined && !searchViewArch) || (!irFilters && loadIrFilters);

        let viewDescription = { viewId, resModel, type };
        let searchViewDescription;
        if (loadView || loadSearchView) {
            // view description (or search view description if required) is incomplete
            // a loadViews is done to complete the missing information
            const options = {
                actionId: this.env.config.actionId,
                loadActionMenus,
                loadIrFilters,
            };
            if (this.env.config.currentEmbeddedActionId) {
                options.embeddedActionId = this.env.config.currentEmbeddedActionId;
                options.embeddedParentResId = context.active_id;
            }
            const result = await this.viewService.loadViews({ context, resModel, views }, options);
            // Note: if props.views is different from views, the cached descriptions
            // will certainly not be reused! (but for the standard flow this will work as
            // before)
            viewDescription = result.views[type];
            searchViewDescription = result.views.search;
            if (loadSearchView) {
                searchViewId = searchViewId || searchViewDescription.id;
                if (!searchViewArch) {
                    searchViewArch = searchViewDescription.arch;
                    searchViewFields = result.fields;
                }
                if (!irFilters) {
                    irFilters = searchViewDescription.irFilters;
                }
            }
            this.env.config.views = views;
            fields = fields || markRaw(result.fields);
            relatedModels = relatedModels || markRaw(result.relatedModels);
        }

        if (!arch) {
            arch = viewDescription.arch;
        }
        if (!actionMenus) {
            actionMenus = viewDescription.actionMenus;
        }

        const archXmlDoc = parseXML(arch.replace(/&amp;nbsp;/g, nbsp));
        for (const action of ACTIONS) {
            if (action in this.props.context && !this.props.context[action]) {
                archXmlDoc.setAttribute(action, "0");
            }
        }

        const jsClass = archXmlDoc.hasAttribute("js_class")
            ? archXmlDoc.getAttribute("js_class")
            : props.jsClass || type;
        if (!viewRegistry.contains(jsClass)) {
            await loadBundle(
                cookie.get("color_scheme") === "dark"
                    ? "web.assets_backend_lazy_dark"
                    : "web.assets_backend_lazy"
            );
        }
        const descr = viewRegistry.get(jsClass);

        const sample = archXmlDoc.getAttribute("sample");
        const className = computeViewClassName(type, archXmlDoc, [
            "o_view_controller",
            ...(props.className || "").split(" "),
        ]);

        Object.assign(this.env.config, {
            rawArch: arch,
            viewArch: archXmlDoc,
            viewId: viewDescription.id,
            viewType: type,
            viewSubType: jsClass,
            noBreadcrumbs: props.noBreadcrumbs,
            ...extractLayoutComponents(descr),
        });
        const info = {
            actionMenus,
            mode: props.display.mode,
            irFilters,
            searchViewArch,
            searchViewFields,
            searchViewId,
        };

        // prepare the view props
        const viewProps = {
            info,
            arch: archXmlDoc,
            fields,
            relatedModels,
            resModel,
            useSampleModel: false,
            className,
        };
        if (viewDescription.custom_view_id) {
            // for dashboard
            viewProps.info.customViewId = viewDescription.custom_view_id;
        }
        if (props.globalState) {
            viewProps.globalState = props.globalState;
        }

        if ("useSampleModel" in props) {
            viewProps.useSampleModel = props.useSampleModel;
        } else if (sample) {
            viewProps.useSampleModel = evaluateBooleanExpr(sample);
        }

        for (const key in props) {
            if (!STANDARD_PROPS.includes(key)) {
                viewProps[key] = props[key];
            }
        }

        const { noContentHelp } = props;
        if (noContentHelp) {
            viewProps.info.noContentHelp = noContentHelp;
        }

        const searchMenuTypes =
            props.searchMenuTypes || descr.searchMenuTypes || this.constructor.searchMenuTypes;
        const defaultGroupBy = archXmlDoc.hasAttribute("default_group_by")
            ? archXmlDoc.getAttribute("default_group_by").split(",")
            : null;
        viewProps.searchMenuTypes = searchMenuTypes;
        const canOrderByCount = descr.canOrderByCount || this.constructor.canOrderByCount;

        const finalProps = descr.props ? descr.props(viewProps, descr, this.env.config) : viewProps;
        // prepare the WithSearch component props
        this.Controller = descr.Controller;
        this.componentProps = finalProps;
        this.withSearchProps = {
            ...toRaw(props),
            hideCustomGroupBy: props.hideCustomGroupBy || descr.hideCustomGroupBy,
            searchMenuTypes,
            canOrderByCount,
            SearchModel: descr.SearchModel,
        };

        if (searchViewId !== undefined) {
            this.withSearchProps.searchViewId = searchViewId;
        }
        if (searchViewArch) {
            this.withSearchProps.searchViewArch = searchViewArch;
            this.withSearchProps.searchViewFields = searchViewFields;
        }
        if (irFilters) {
            this.withSearchProps.irFilters = irFilters;
        }

        if (descr.display) {
            // FIXME: there's something inelegant here: display might come from
            // the View's defaultProps, in which case, modifying it in place
            // would have unwanted effects.
            const viewDisplay = deepCopy(descr.display);
            const display = { ...this.withSearchProps.display };
            for (const key in viewDisplay) {
                if (typeof display[key] === "object") {
                    Object.assign(display[key], viewDisplay[key]);
                } else if (!(key in display) || display[key]) {
                    display[key] = viewDisplay[key];
                }
            }
            this.withSearchProps.display = display;
        }

        if (defaultGroupBy && defaultGroupBy.length) {
            this.withSearchProps.defaultGroupBy = defaultGroupBy;
        }

        for (const key in this.withSearchProps) {
            if (!(key in WithSearch.props)) {
                delete this.withSearchProps[key];
            }
        }
    }

    /**
     * @param {ViewProps} nextProps
     */
    onWillUpdateProps(nextProps) {
        const oldProps = pick(this.props, "arch", "type", "resModel");
        const newProps = pick(nextProps, "arch", "type", "resModel");
        if (JSON.stringify(oldProps) !== JSON.stringify(newProps)) {
            return this.loadView(nextProps);
        }
        // we assume that nextProps can only vary in the search keys:
        // context, domain, groupBy, orderBy
        const { context, domain, groupBy, orderBy } = nextProps;
        Object.assign(this.withSearchProps, { context, domain, groupBy, orderBy });
    }
}
