import { Component, onWillRender, xml } from "@odoo/owl";
import { escapeRegExp } from "@web/core/utils/strings";
import { zip } from "@web/core/utils/arrays";
import { useService } from "@web/core/utils/hooks";

function parseParams(matches, paramSpecs) {
    return Object.fromEntries(
        zip(matches, paramSpecs).map(([match, paramSpec]) => {
            const { type, name } = paramSpec;
            switch (type) {
                case "int":
                    return [name, parseInt(match)];
                case "string":
                    return [name, match];
                default:
                    throw new Error(`Unknown type ${type}`);
            }
        })
    );
}

export class Router extends Component {
    static props = { slots: Object, pos_config_id: Number };
    static template = xml`<t t-slot="{{activeSlot}}" t-props="slotProps"/>`;

    setup() {
        this.router = useService("router");
        this.activeSlot = "default";
        this.slotProps = {};
        this.routes = {};
        const lgPrefixRegex = "^(?:/([a-zA-Z]{2}(?:_[a-zA-Z]{2})?))?"; // optional language code: e.g. fr/ or fr_be/

        for (const [routeName, slot] of Object.entries(this.props.slots)) {
            const route = slot.route;
            const paramStrings = route.match(/\{\w+:\w+\}/g);

            if (!paramStrings) {
                this.routes[routeName] = {
                    route,
                    paramSpecs: [],
                    regex: new RegExp(`${lgPrefixRegex}${route}$`),
                };
                continue;
            }

            const paramSpecs = paramStrings.map((paramString) => {
                const [, type, name] = paramString.match(/(\w+):(\w+)/);
                return { type, name };
            });

            const regex = new RegExp(
                `${lgPrefixRegex}${route
                    .split(/\{\w+:\w+\}/)
                    .map((part) => escapeRegExp(part))
                    .join("([^/]+)")}$`
            );

            this.routes[routeName] = { route, paramSpecs, regex };
        }

        this.router.registerRoutes(this.routes);

        onWillRender(() => {
            this.matchURL();
        });
    }

    matchURL() {
        const path = this.router.path;

        for (const [routeName, { paramSpecs, regex }] of Object.entries(this.routes)) {
            const match = path.match(regex);
            if (match) {
                const parsedParams = parseParams(match.slice(2), paramSpecs);
                this.router.activeSlot = routeName;
                this.activeSlot = routeName;
                this.slotProps = parsedParams;
                return;
            }
        }

        this.router.activeSlot = "default";
        this.router.navigate("default");
    }
}
