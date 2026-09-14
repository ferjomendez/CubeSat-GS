import "@testing-library/jest-dom/vitest";

// jsdom has no layout engine: every element reports 0x0 for offsetWidth/offsetHeight and
// getBoundingClientRect, and has no ResizeObserver. @tanstack/react-virtual (used by LiveFeed)
// relies on real, non-zero measurements to size its scroll viewport and rows — accommodate that
// here, in the test harness, rather than in the shipped component.
Object.defineProperty(HTMLElement.prototype, "offsetWidth", { configurable: true, value: 800 });
Object.defineProperty(HTMLElement.prototype, "offsetHeight", { configurable: true, value: 600 });

const rect: DOMRect = {
  width: 800,
  height: 600,
  top: 0,
  left: 0,
  right: 800,
  bottom: 600,
  x: 0,
  y: 0,
  toJSON() {
    return this;
  },
};
Element.prototype.getBoundingClientRect = () => rect;

if (typeof ResizeObserver === "undefined") {
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  globalThis.ResizeObserver = ResizeObserverStub;
}
