/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { debounce } from "@web/core/utils/timing";
import { _legacyIsVisible, isVisible } from "@web/core/utils/ui";
import { omit } from "@web/core/utils/objects";
import { tourState } from "./tour_state";
import * as hoot from "@odoo/hoot-dom";
import { session } from "@web/session";
import { setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
import { callWithUnloadCheck, getConsumeEventType, getScrollParent } from "./tour_utils";
import { utils } from "@web/core/ui/ui_service";
import { TourHelpers } from "./tour_helpers";

/**
 * @typedef {import("@web/core/macro").MacroDescriptor} MacroDescriptor
 *
 * @typedef {import("../tour_service/tour_pointer_state").TourPointerState} TourPointerState
 *
 * @typedef {import("./tour_service").TourStep} TourStep
 *
 * @typedef {(stepIndex: number, step: TourStep, options: TourCompilerOptions) => MacroDescriptor[]} TourStepCompiler
 *
 * @typedef TourCompilerOptions
 * @property {Tour} tour
 * @property {number} stepDelay
 * @property {keepWatchBrowser} boolean
 * @property {showPointerDuration} number
 * @property {*} pointer - used for controlling the pointer of the tour
 */

/**
 * @param {string} selector - any valid Hoot selector
 * @param {boolean} inModal
 * @returns {Array<Element>}
 */
function findTrigger(selector, inModal) {
    let nodes;
    if (inModal !== false) {
        const visibleModal = hoot.queryAll(".modal", { visible: true }).at(-1);
        if (visibleModal) {
            nodes = hoot.queryAll(selector, { root: visibleModal });
        }
    }
    if (!nodes) {
        nodes = hoot.queryAll(selector);
    }
    return nodes;
}

/**
 * @param {Tour} tour
 * @param {TourStep} step
 * @param {"trigger"|"extra_trigger"|"alt_trigger"} elKey
 * @returns {HTMLElement|null}
 */
function tryFindTrigger(tour, step, elKey) {
    const selector = step[elKey];
    const in_modal = elKey === "extra_trigger" ? false : step.in_modal;
    try {
        const nodes = findTrigger(selector, in_modal);
        //TODO : change _legacyIsVisible by isVisible (hoot lib)
        //Failed with tour test_snippet_popup_with_scrollbar_and_animations > snippet_popup_and_animations
        return !step.allowInvisible ? nodes.find(_legacyIsVisible) : nodes.at(0);
    } catch (error) {
        throwError(tour, step, [`Trigger was not found : ${selector} : ${error.message}`]);
    }
}

function findStepTriggers(tour, step) {
    const triggerEl = tryFindTrigger(tour, step, "trigger");
    const altEl = tryFindTrigger(tour, step, "alt_trigger");
    const extraEl = tryFindTrigger(tour, step, "extra_trigger");
    step.state = step.state || {};
    step.state.triggerFound = !!triggerEl;
    step.state.altTriggerFound = !!altEl;
    step.state.extraTriggerFound = step.extra_trigger ? !!extraEl : true;
    // `extraTriggerOkay` should be true when `step.extra_trigger` is undefined.
    // No need for it to be in the modal.
    const extraTriggerOkay = step.state.extraTriggerFound;
    return { triggerEl, altEl, extraEl, extraTriggerOkay };
}

/**
 * @param {TourStep} step
 */
function describeStep(step) {
    return step.content ? `${step.content} (trigger: ${step.trigger})` : step.trigger;
}

/**
 * @param {TourStep} step
 */
function describeFailedStepSimple(tour, step) {
    return `Tour ${tour.name} failed at step ${describeStep(step)}`;
}

function describeWhyStepFailed(step) {
    const stepState = step.state || {};
    if (step.extra_trigger && !stepState.extraTriggerFound) {
        return `The cause is that extra trigger (${step.extra_trigger}) element cannot be found in DOM.`;
    } else if (!stepState.triggerFound) {
        return `The cause is that trigger (${step.trigger}) element cannot be found in DOM.`;
    } else if (step.alt_trigger && !stepState.altTriggerFound) {
        return `The cause is that alt(ernative) trigger (${step.alt_trigger}) element cannot be found in DOM.`;
    } else if (!stepState.isVisible) {
        return "Element has been found but isn't displayed. (Use 'step.allowInvisible: true,' if you want to skip this check)";
    } else if (!stepState.isEnabled) {
        return "Element has been found but is disabled.";
    } else if (stepState.isBlocked) {
        return "Element has been found but DOM is blocked by UI.";
    } else if (!stepState.hasRun) {
        return `Element has been found. The error seems to be with step.run`;
    }
    return "";
}

/**
 * @param {TourStep} step
 * @param {Tour} tour
 */
function describeFailedStepDetailed(tour, step) {
    const offset = 3;
    const stepIndex = tour.steps.findIndex((s) => s === step);
    const start = stepIndex - offset >= 0 ? stepIndex - offset : 0;
    const end =
        stepIndex + offset + 1 <= tour.steps.length ? stepIndex + offset + 1 : tour.steps.length;
    const result = [describeFailedStepSimple(tour, step)];
    for (let i = start; i < end; i++) {
        const stepString =
            JSON.stringify(
                omit(tour.steps[i], "state"),
                (_key, value) => {
                    if (typeof value === "function") {
                        return "[function]";
                    } else {
                        return value;
                    }
                },
                2
            ) + ",";
        const text = [stepString];
        if (i === stepIndex) {
            const line = "-".repeat(10);
            const failing_step = `${line} FAILING STEP (${i + 1}/${tour.steps.length}) ${line}`;
            text.unshift(failing_step);
            text.push("-".repeat(failing_step.length));
        }
        result.push(...text);
    }
    return result.join("\n");
}

/**
 * Returns the element that will be used in listening to the `consumeEvent`.
 * @param {HTMLElement} el
 * @param {string} consumeEvent
 */
function getAnchorEl(el, consumeEvent) {
    if (consumeEvent === "drag") {
        // jQuery-ui draggable triggers 'drag' events on the .ui-draggable element,
        // but the tip is attached to the .ui-draggable-handle element which may
        // be one of its children (or the element itself)
        return el.closest(".ui-draggable, .o_draggable");
    }
    if (consumeEvent === "input" && !["textarea", "input"].includes(el.tagName.toLowerCase())) {
        return el.closest("[contenteditable='true']");
    }
    if (consumeEvent === "sort") {
        // when an element is dragged inside a sortable container (with classname
        // 'ui-sortable'), jQuery triggers the 'sort' event on the container
        return el.closest(".ui-sortable, .o_sortable");
    }
    return el;
}

/**
 * Check if a step is active dependant on step.isActive property
 * Note that when step.isActive is not defined, the step is active by default.
 * When a step is not active, it's just skipped and the tour continues to the next step.
 * @param {TourStep} step
 * @param {TourMode} mode TourMode manual means onboarding tour
 */
function isActive(step, mode) {
    const isSmall = utils.isSmall();
    const standardKeyWords = ["enterprise", "community", "mobile", "desktop", "auto", "manual"];
    const isActiveArray = Array.isArray(step.isActive) ? step.isActive : [];
    if (isActiveArray.length === 0) {
        return true;
    }
    const selectors = isActiveArray.filter((key) => !standardKeyWords.includes(key));
    if (selectors.length) {
        // if one of selectors is not found, step is skipped
        for (const selector of selectors) {
            const el = hoot.queryFirst(selector);
            if (!el) {
                return false;
            }
        }
    }
    const checkMode =
        isActiveArray.includes(mode) ||
        (!isActiveArray.includes("manual") && !isActiveArray.includes("auto"));
    const edition = (session.server_version_info || "").at(-1) === "e" ? "enterprise" : "community";
    const checkEdition =
        isActiveArray.includes(edition) ||
        (!isActiveArray.includes("enterprise") && !isActiveArray.includes("community"));
    const onlyForMobile = isActiveArray.includes("mobile") && isSmall;
    const onlyForDesktop = isActiveArray.includes("desktop") && !isSmall;
    const checkDevice =
        onlyForMobile ||
        onlyForDesktop ||
        (!isActiveArray.includes("mobile") && !isActiveArray.includes("desktop"));
    return checkEdition && checkDevice && checkMode;
}

/**
 * IMPROVEMENT: Consider transitioning (moving) elements?
 * @param {Element} el
 * @param {TourStep} step
 */
function canContinue(el, step) {
    step.state = step.state || {};
    const state = step.state;
    const rootNode = el.getRootNode();
    state.isInDoc =
        rootNode instanceof ShadowRoot
            ? el.ownerDocument.contains(rootNode.host)
            : el.ownerDocument.contains(el);
    state.isElement = el instanceof el.ownerDocument.defaultView.Element || el instanceof Element;
    state.isVisible = step.allowInvisible || isVisible(el);
    const isBlocked =
        document.body.classList.contains("o_ui_blocked") || document.querySelector(".o_blockUI");
    state.isBlocked = !!isBlocked;
    state.isEnabled = step.allowDisabled || !el.disabled;
    state.canContinue = !!(
        state.isInDoc &&
        state.isElement &&
        state.isVisible &&
        state.isEnabled &&
        !state.isBlocked
    );
    return state.canContinue;
}

function getStepState(step) {
    step.state = step.state || {};
    const checkRun =
        (["string", "function"].includes(typeof step.run) && step.state.hasRun) || !step.run;
    const check = checkRun && step.state.canContinue;
    return check ? "succeeded" : "errored";
}

/**
 * @param {TourStep} step
 * @param {Tour} tour
 * @param {Array<string>} [errors]
 */
function throwError(tour, step, errors = []) {
    const debugMode = tourState.get(tour.name, "debug");
    // The logged text shows the relative position of the failed step.
    // Useful for finding the failed step.
    console.warn(describeFailedStepDetailed(tour, step));
    // console.error notifies the test runner that the tour failed.
    console.error(`${describeFailedStepSimple(tour, step)}. ${describeWhyStepFailed(step)}`);
    if (errors.length) {
        console.error(errors.join(", "));
    }
    if (debugMode !== false) {
        // eslint-disable-next-line no-debugger
        debugger;
    }
}

/**
 * @param {Object} params
 * @param {HTMLElement} params.anchorEl
 * @param {string} params.consumeEvent
 * @param {() => void} params.onMouseEnter
 * @param {() => void} params.onMouseLeave
 * @param {(ev: Event) => any} params.onScroll
 * @param {(ev: Event) => any} params.onConsume
 */
function setupListeners({
    anchorEl,
    consumeEvent,
    onMouseEnter,
    onMouseLeave,
    onScroll,
    onConsume,
}) {
    anchorEl.addEventListener(consumeEvent, onConsume);
    anchorEl.addEventListener("mouseenter", onMouseEnter);
    anchorEl.addEventListener("mouseleave", onMouseLeave);

    const cleanups = [
        () => {
            anchorEl.removeEventListener(consumeEvent, onConsume);
            anchorEl.removeEventListener("mouseenter", onMouseEnter);
            anchorEl.removeEventListener("mouseleave", onMouseLeave);
        },
    ];

    const scrollEl = getScrollParent(anchorEl);
    if (scrollEl) {
        const debouncedOnScroll = debounce(onScroll, 50);
        scrollEl.addEventListener("scroll", debouncedOnScroll);
        cleanups.push(() => scrollEl.removeEventListener("scroll", debouncedOnScroll));
    }

    return () => {
        while (cleanups.length) {
            cleanups.pop()();
        }
    };
}

/** @type {TourStepCompiler} */
export function compileStepManual(stepIndex, step, options) {
    const { tour, pointer, onStepConsummed } = options;
    let proceedWith = null;
    let removeListeners = () => {};

    return [
        {
            action: () => console.log(step.trigger),
        },
        {
            trigger: () => {
                removeListeners();
                if (!isActive(step, "manual")) {
                    return hoot.queryFirst("body");
                }
                if (proceedWith) {
                    return proceedWith;
                }

                const { triggerEl, altEl, extraTriggerOkay } = findStepTriggers(tour, step);

                const stepEl = extraTriggerOkay && (triggerEl || altEl);

                if (stepEl && canContinue(stepEl, step)) {
                    const consumeEvent = step.consumeEvent || getConsumeEventType(stepEl, step.run);
                    const anchorEl = getAnchorEl(stepEl, consumeEvent);
                    const debouncedToggleOpen = debounce(pointer.showContent, 50, true);

                    const updatePointer = () => {
                        pointer.setState({
                            onMouseEnter: () => debouncedToggleOpen(true),
                            onMouseLeave: () => debouncedToggleOpen(false),
                        });
                        pointer.pointTo(anchorEl, step);
                    };

                    removeListeners = setupListeners({
                        anchorEl,
                        consumeEvent,
                        onMouseEnter: () => pointer.showContent(true),
                        onMouseLeave: () => pointer.showContent(false),
                        onScroll: updatePointer,
                        onConsume: () => {
                            proceedWith = stepEl;
                            pointer.hide();
                        },
                    });

                    updatePointer();
                } else {
                    pointer.hide();
                }
            },
            action: () => {
                tourState.set(tour.name, "currentIndex", stepIndex + 1);
                tourState.set(tour.name, "stepState", "succeeded");
                pointer.hide();
                proceedWith = null;
                onStepConsummed(tour, step);
            },
        },
    ];
}

let tourTimeout;

/**
 * @type {TourStepCompiler}
 * @param {number} stepIndex
 * @param {TourStep} step
 * @param {object} options
 * @returns {{trigger, action}[]}
 */
export function compileStepAuto(stepIndex, step, options) {
    const { tour, pointer, stepDelay } = options;
    const { showPointerDuration, onStepConsummed } = options;
    const debugMode = tourState.get(tour.name, "debug");

    async function tryToDoAction(action) {
        try {
            await action();
            step.state.hasRun = true;
        } catch (error) {
            throwError(tour, step, [error.message]);
        }
    }

    return [
        {
            action: () => {
                setupEventActions(document.createElement("div"));
                step.state = step.state || {};
                if (step.break && debugMode !== false) {
                    // eslint-disable-next-line no-debugger
                    debugger;
                }
            },
        },
        {
            action: async () => {
                console.log(`Tour ${tour.name} on step: '${describeStep(step)}'`);
                tourTimeout = browser.setTimeout(
                    () => throwError(tour, step),
                    (step.timeout || 10000) + stepDelay
                );
                // This delay is important for making the current set of tour tests pass.
                // IMPROVEMENT: Find a way to remove this delay.
                await new Promise((resolve) => requestAnimationFrame(resolve));
                await new Promise((resolve) => browser.setTimeout(resolve, stepDelay));
            },
        },
        {
            trigger: () => {
                if (!isActive(step, "auto")) {
                    step.run = () => {};
                    step.state.canContinue = true;
                    return hoot.queryFirst("body");
                }
                const { triggerEl, altEl, extraTriggerOkay } = findStepTriggers(tour, step);
                const stepEl = extraTriggerOkay && (triggerEl || altEl);
                if (!stepEl) {
                    return false;
                }

                return canContinue(stepEl, step) && stepEl;
            },
            action: async (stepEl) => {
                //if stepEl is found, timeout can be cleared.
                browser.clearTimeout(tourTimeout);
                tourState.set(tour.name, "currentIndex", stepIndex + 1);

                if (showPointerDuration > 0) {
                    // Useful in watch mode.
                    pointer.pointTo(stepEl, step);
                    await new Promise((r) => browser.setTimeout(r, showPointerDuration));
                    pointer.hide();
                }

                // TODO: Delegate the following routine to the `ACTION_HELPERS` in the macro module.
                const actionHelper = new TourHelpers(stepEl);

                let result;
                if (typeof step.run === "function") {
                    const willUnload = await callWithUnloadCheck(async () => {
                        await tryToDoAction(() =>
                            // `this.anchor` is expected in many `step.run`.
                            step.run.call({ anchor: stepEl }, actionHelper)
                        );
                    });
                    result = willUnload && "will unload";
                } else if (typeof step.run === "string") {
                    for (const todo of step.run.split("&&")) {
                        const m = String(todo)
                            .trim()
                            .match(/^(?<action>\w*) *\(? *(?<arguments>.*?)\)?$/);
                        await tryToDoAction(() =>
                            actionHelper[m.groups?.action](m.groups?.arguments)
                        );
                    }
                }
                return result;
            },
        },
        {
            action: () => {
                tourState.set(tour.name, "stepState", getStepState(step));
                onStepConsummed(tour, step);
            },
        },
        {
            action: async () => {
                if (step.pause && debugMode !== false) {
                    const styles = [
                        "background: black; color: white; font-size: 14px",
                        "background: black; color: orange; font-size: 14px",
                    ];
                    console.log(
                        `%cTour is paused. Use %cplay()%c to continue.`,
                        styles[0],
                        styles[1],
                        styles[0]
                    );
                    window.hoot = hoot;
                    await new Promise((resolve) => {
                        window.play = () => {
                            resolve();
                            delete window.play;
                            delete window.hoot;
                        };
                    });
                }
            },
        },
    ];
}

/**
 * @param {import("./tour_service").Tour} tour
 * @param {object} options
 * @param {TourStep[]} options.filteredSteps
 * @param {TourStepCompiler} options.stepCompiler
 * @param {*} options.pointer
 * @param {number} options.stepDelay
 * @param {boolean} options.keepWatchBrowser
 * @param {number} options.showPointerDuration
 * @param {number} options.checkDelay
 * @param {(import("./tour_service").Tour) => void} options.onTourEnd
 */
export function compileTourToMacro(tour, options) {
    const {
        filteredSteps,
        stepCompiler,
        pointer,
        stepDelay,
        keepWatchBrowser,
        showPointerDuration,
        checkDelay,
        onStepConsummed,
        onTourEnd,
    } = options;
    const currentStepIndex = tourState.get(tour.name, "currentIndex");
    return {
        ...tour,
        checkDelay,
        steps: filteredSteps
            .reduce((newSteps, step, i) => {
                if (i < currentStepIndex) {
                    // Don't include steps before the current index because they're already done.
                    return newSteps;
                } else {
                    return [
                        ...newSteps,
                        ...stepCompiler(i, step, {
                            tour,
                            pointer,
                            stepDelay,
                            keepWatchBrowser,
                            showPointerDuration,
                            onStepConsummed,
                        }),
                    ];
                }
            }, [])
            .concat([
                {
                    action() {
                        clearTimeout(tourTimeout);
                        if (tourState.get(tour.name, "stepState") === "succeeded") {
                            tourState.clear(tour.name);
                            onTourEnd(tour);
                        } else {
                            console.error("tour not succeeded");
                        }
                    },
                },
            ]),
    };
}
