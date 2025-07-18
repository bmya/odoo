import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { DropdownGroup } from "@web/core/dropdown/dropdown_group";
import { Transition } from "@web/core/transition";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";
import { ErrorHandler } from "@web/core/utils/components";

import {
    Component,
    onWillDestroy,
    useExternalListener,
    useEffect,
    useRef,
    useState,
    onWillUnmount,
} from "@odoo/owl";
const systrayRegistry = registry.category("systray");

const getBoundingClientRect = Element.prototype.getBoundingClientRect;

const SWIPE_ACTIVATION_THRESHOLD = 100;

export class MenuDropdown extends Dropdown {}

export class NavBar extends Component {
    static template = "web.NavBar";
    static components = {
        Dropdown,
        DropdownItem,
        DropdownGroup,
        MenuDropdown,
        ErrorHandler,
        Transition,
    };
    static props = {};

    setup() {
        this.currentAppSectionsExtra = [];
        this.actionService = useService("action");
        this.menuService = useService("menu");
        this.pwa = useService("pwa");
        this.root = useRef("root");
        this.appSubMenus = useRef("appSubMenus");
        const debouncedAdapt = debounce(this.adapt.bind(this), 250);
        onWillDestroy(() => debouncedAdapt.cancel());
        useExternalListener(window, "resize", debouncedAdapt);

        let adaptCounter = 0;
        const renderAndAdapt = () => {
            adaptCounter++;
            this.render();
        };

        systrayRegistry.addEventListener("UPDATE", renderAndAdapt);
        this.env.bus.addEventListener("MENUS:APP-CHANGED", renderAndAdapt);

        onWillUnmount(() => {
            systrayRegistry.removeEventListener("UPDATE", renderAndAdapt);
            this.env.bus.removeEventListener("MENUS:APP-CHANGED", renderAndAdapt);
        });

        // We don't want to adapt every time we are patched
        // rather, we adapt only when menus or systrays have changed.
        useEffect(
            () => {
                this.adapt();
            },
            () => [adaptCounter]
        );

        this.state = useState({
            isAllAppsMenuOpened: false,
            isAppMenuSidebarOpened: false,
        });
    }

    handleItemError(error, item) {
        // remove the faulty component
        item.isDisplayed = () => false;
        Promise.resolve().then(() => {
            throw error;
        });
    }

    get currentApp() {
        return this.menuService.getCurrentApp();
    }

    get currentAppSections() {
        return (
            (this.currentApp && this.menuService.getMenuAsTree(this.currentApp.id).childrenTree) ||
            []
        );
    }

    // This dummy setter is only here to prevent conflicts between the
    // Enterprise NavBar extension and the Website NavBar patch.
    set currentAppSections(_) {}

    get isScopedApp() {
        return this.pwa.isScopedApp;
    }

    get systrayItems() {
        return systrayRegistry
            .getEntries()
            .map(([key, value]) => ({ key, ...value }))
            .filter((item) => ("isDisplayed" in item ? item.isDisplayed(this.env) : true))
            .reverse();
    }

    // This dummy setter is only here to prevent conflicts between the
    // Enterprise NavBar extension and the Website NavBar patch.
    set systrayItems(_) {}

    /**
     * Adapt will check the available width for the app sections to get displayed.
     * If not enough space is available, it will replace by a "more" menu
     * the least amount of app sections needed trying to fit the width.
     *
     * NB: To compute the widths of the actual app sections, a render needs to be done upfront.
     *     By the end of this method another render may occur depending on the adaptation result.
     */
    async adapt() {
        if (!this.root.el) {
            /** @todo do we still need this check? */
            // currently, the promise returned by 'render' is resolved at the end of
            // the rendering even if the component has been destroyed meanwhile, so we
            // may get here and have this.el unset
            return;
        }

        // ------- Initialize -------
        // Get the sectionsMenu
        const sectionsMenu = this.appSubMenus.el;
        if (!sectionsMenu) {
            // No need to continue adaptations if there is no sections menu.
            return;
        }

        // Save initial state to further check if new render has to be done.
        const initialAppSectionsExtra = this.currentAppSectionsExtra;
        const firstInitialAppSectionExtra = [...initialAppSectionsExtra].shift();
        const initialAppId = firstInitialAppSectionExtra && firstInitialAppSectionExtra.appID;

        // Restore (needed to get offset widths)
        const sections = [
            ...sectionsMenu.querySelectorAll(":scope > *:not(.o_menu_sections_more)"),
        ];
        for (const section of sections) {
            section.classList.remove("d-none");
        }
        this.currentAppSectionsExtra = [];

        // ------- Check overflowing sections -------
        // use getBoundingClientRect to get unrounded values for width in order to avoid rounding problem
        // with offsetWidth.
        const sectionsAvailableWidth = getBoundingClientRect.call(sectionsMenu).width;
        const sectionsTotalWidth = sections.reduce(
            (sum, s) => sum + getBoundingClientRect.call(s).width,
            0
        );
        if (sectionsAvailableWidth < sectionsTotalWidth) {
            // Sections are overflowing
            // Initial width is harcoded to the width the more menu dropdown will take
            let width = 46;
            for (const section of sections) {
                if (sectionsAvailableWidth < width + section.offsetWidth) {
                    // Last sections are overflowing
                    const overflowingSections = sections.slice(sections.indexOf(section));
                    overflowingSections.forEach((s) => {
                        // Hide from normal menu
                        s.classList.add("d-none");
                        // Show inside "more" menu
                        const sectionId =
                            s.dataset.section ||
                            s.querySelector("[data-section]").getAttribute("data-section");
                        const currentAppSection = this.currentAppSections.find(
                            (appSection) => appSection.id.toString() === sectionId
                        );
                        this.currentAppSectionsExtra.push(currentAppSection);
                    });
                    break;
                }
                width += section.offsetWidth;
            }
        }

        // ------- Final rendering -------
        const firstCurrentAppSectionExtra = [...this.currentAppSectionsExtra].shift();
        const currentAppId = firstCurrentAppSectionExtra && firstCurrentAppSectionExtra.appID;
        if (
            initialAppSectionsExtra.length === this.currentAppSectionsExtra.length &&
            initialAppId === currentAppId
        ) {
            // Do not render if more menu items stayed the same.
            return;
        }
        return this.render();
    }

    onNavBarDropdownItemSelection(menu) {
        if (menu) {
            this.menuService.selectMenu(menu);
        }
    }

    getMenuItemHref(payload) {
        return `/odoo/${payload.actionPath || "action-" + payload.actionID}`;
    }

    _closeAppMenuSidebar() {
        this.state.isAllAppsMenuOpened = false;
        this.state.isAppMenuSidebarOpened = false;
    }
    _openAppMenuSidebar() {
        this.state.isAppMenuSidebarOpened = !this.state.isAppMenuSidebarOpened;
    }
    onAllAppsBtnClick() {
        this.state.isAllAppsMenuOpened = !this.state.isAllAppsMenuOpened;
    }
    async _onMenuClicked(menu) {
        await this.menuService.selectMenu(menu);
        this._closeAppMenuSidebar();
    }
    _onSwipeStart(ev) {
        this.swipeStartX = ev.changedTouches[0].clientX;
    }
    _onSwipeEnd(ev) {
        if (!this.swipeStartX) {
            return;
        }
        const deltaX = this.swipeStartX - ev.changedTouches[0].clientX;
        if (deltaX < SWIPE_ACTIVATION_THRESHOLD) {
            return;
        }
        this._closeAppMenuSidebar();
        this.swipeStartX = null;
    }
}
