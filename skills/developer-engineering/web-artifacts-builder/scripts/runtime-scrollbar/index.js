/**
 * Original project-local runtime, implemented from the documented public contract.
 *
 * Usage: render <RemoveScrollBar /> while a modal is open. It renders null. Each
 * Document has one lock; the earliest still-mounted instance selects gapMode
 * (default margin), noRelative and noImportant. StrictMode cleanup is idempotent.
 * noRelative keeps position untouched; otherwise only a static body becomes
 * relative. noImportant omits !important, allowing author CSS to win the cascade.
 *
 * getGapWidth returns computed physical left/top/right margin (or padding) and
 * max(0, innerWidth - documentElement.clientWidth), not a margin-adjusted gutter.
 * While locked it describes the current, locked viewport. On resize we briefly
 * restore owned styles synchronously to measure the natural gutter, then lock
 * again. Compensation is the gutter actually removed, so stable gutters and
 * overlay scrollbars need no extra space. Existing spacing is added only once.
 *
 * For a conventional root vertical scrollbar, clientLeft minus root border-left
 * identifies a left gutter (including RTL engines that put it there). Direction
 * alone does not predict scrollbar placement. No promise is made for transformed
 * roots, vertical writing modes, custom scroll containers or mobile touch locks.
 * Body fixed widths/containing blocks can need application-specific styling.
 *
 * Scoped classes support fixed elements anchored at gutter-edge zero, elements
 * initially width:100%, and overflow-hidden elements, respectively. They replace
 * that edge/width; they do not infer arbitrary offsets. CSP must allow these
 * inline styles and the inserted style element (no nonce API is provided).
 *
 * Restoration compares values AND priorities; externally changed owned fields
 * are relinquished for the rest of this lock. Unrelated declarations are never
 * rewritten. Same-value external writes are indistinguishable from our writes.
 * External edits to our style text are not overwritten during a lock; the node
 * itself remains ours and is removed at final cleanup. Setup errors propagate
 * after rollback; missing DOM is a no-op. No imports other than React are used.
 */
import { useEffect, useLayoutEffect } from 'react';

export const zeroRightClassName = 'right-scroll-bar-position';
export const fullWidthClassName = 'width-before-scroll-bar';
export const noScrollbarsClassName = 'with-scroll-bars-hidden';
export const removedBarSizeVariable = '--removed-body-scroll-bar-size';

const documents = new WeakMap();
const scopeAttribute = 'data-hvs-scrollbar-compensation';
const useClientEffect = typeof window === 'undefined' ? useEffect : useLayoutEffect;
let nextScope = 0;

const numeric = (value) => Number.isFinite(parseFloat(value)) ? parseFloat(value) : 0;
const pair = (style, name) => [style.getPropertyValue(name), style.getPropertyPriority(name)];
const same = (a, b) => a[0] === b[0] && a[1] === b[1];

function available(doc) {
  return !!(doc && doc.body && doc.documentElement && doc.defaultView);
}

function measure(doc, mode) {
  if (!available(doc)) return { left: 0, top: 0, right: 0, gap: 0 };
  const computed = doc.defaultView.getComputedStyle(doc.body);
  const gap = doc.defaultView.innerWidth - doc.documentElement.clientWidth;
  return {
    left: numeric(computed.getPropertyValue(`${mode}-left`)),
    top: numeric(computed.getPropertyValue(`${mode}-top`)),
    right: numeric(computed.getPropertyValue(`${mode}-right`)),
    gap: Number.isFinite(gap) ? Math.max(0, gap) : 0,
  };
}

export function getGapWidth(gapMode = 'margin') {
  return measure(typeof document === 'undefined' ? null : document, gapMode);
}

// Snapshot just a property group, preserving authored shorthand entries/order.
function entries(style, names) {
  return Array.from({ length: style.length }, (_, i) => style.item(i))
    .filter((name) => names.includes(name))
    .map((name) => [name, ...pair(style, name)]);
}

function writeStyle(state, name, value, priority) {
  if (state.relinquished.has(name)) return;
  const style = state.body.style;
  const family = name.startsWith('margin-') ? 'margin' : name.startsWith('padding-') ? 'padding' : null;
  const names = name === 'overflow' ? ['overflow', 'overflow-x', 'overflow-y']
    : family ? [family, ...['top', 'right', 'bottom', 'left'].map((edge) => `${family}-${edge}`)] : [name];
  const before = entries(style, names);
  const beforeValues = names.map((key) => pair(style, key));
  // Journal before mutating, so a setter failure can still be rolled back.
  const record = { name, names, before, beforeValues, after: before, afterValues: beforeValues };
  state.styles.push(record);
  try {
    style.setProperty(name, value, priority);
  } finally {
    record.after = entries(style, names);
    record.afterValues = names.map((key) => pair(style, key));
  }
}

function restoreStyles(state) {
  const style = state.body.style;
  for (const record of state.styles.splice(0).reverse()) {
    const { name, names, before, beforeValues, after, afterValues } = record;
    if (JSON.stringify(entries(style, names)) === JSON.stringify(after)) {
      for (const key of names) style.removeProperty(key);
      for (const [key, value, priority] of before) style.setProperty(key, value, priority);
    } else {
      if (name === 'overflow' || !same(pair(style, name), afterValues[names.indexOf(name)])) {
        state.relinquished.add(name);
      }
      // Preserve external edits to a shorthand family, freeing only our changes.
      for (let i = 1; i < names.length; i += 1) {
        if (!same(beforeValues[i], afterValues[i]) && same(pair(style, names[i]), afterValues[i])) {
          const [value, priority] = beforeValues[i];
          if (value) style.setProperty(names[i], value, priority);
          else style.removeProperty(names[i]);
        }
      }
    }
  }
}

function writeAttribute(state, name, value) {
  let record = state.attributes.get(name);
  if (!record) {
    record = { before: state.body.getAttribute(name), after: state.body.getAttribute(name), blocked: false };
    state.attributes.set(name, record);
  }
  if (state.body.getAttribute(name) !== record.after) record.blocked = true;
  if (!record.blocked) {
    state.body.setAttribute(name, value);
    record.after = value;
  }
}

function refresh(state) {
  restoreStyles(state);
  const { doc, body, view } = state;
  const options = state.leases.values().next().value;
  const spacing = measure(doc, options.gapMode);
  const rootBorder = numeric(view.getComputedStyle(doc.documentElement).getPropertyValue('border-left-width'));
  const side = spacing.gap > 0 && doc.documentElement.clientLeft - rootBorder > spacing.gap / 2
    ? 'left' : 'right';
  const position = view.getComputedStyle(body).getPropertyValue('position');
  const priority = options.noImportant ? '' : 'important';
  writeStyle(state, 'overflow', 'hidden', priority);
  const removed = Math.max(0, spacing.gap - measure(doc, options.gapMode).gap);
  if (!options.noRelative && position === 'static') writeStyle(state, 'position', 'relative', priority);
  if (removed > 0) {
    writeStyle(state, `${options.gapMode}-${side}`, `${spacing[side] + removed}px`, priority);
  }
  writeStyle(state, removedBarSizeVariable, `${removed}px`, priority);
  writeAttribute(state, scopeAttribute, state.scope);
  writeAttribute(state, 'data-scroll-locked', String(state.initialCount + state.leases.size));

  const selector = `body[${scopeAttribute}="${state.scope}"]`;
  const important = options.noImportant ? '' : ' !important';
  const rule = (className, declarations) => `${selector}.${className},${selector} .${className}{${declarations}}`;
  const css = [
    rule(zeroRightClassName, `${side}:var(${removedBarSizeVariable},0px)${important};`),
    rule(fullWidthClassName, `width:calc(100% - var(${removedBarSizeVariable},0px))${important};`),
    rule(noScrollbarsClassName, `overflow:hidden${important};`),
  ].join('\n');
  if (state.style.textContent !== state.css) state.styleChanged = true;
  if (!state.styleChanged) {
    state.style.textContent = css;
    state.css = css;
  }
}

function dispose(state) {
  state.view.removeEventListener('resize', state.resize);
  restoreStyles(state);
  for (const [name, record] of state.attributes) {
    if (!record.blocked && state.body.getAttribute(name) === record.after) {
      if (record.before === null) state.body.removeAttribute(name);
      else state.body.setAttribute(name, record.before);
    }
  }
  if (state.style) state.style.remove();
  documents.delete(state.doc);
}

function acquire(doc, options) {
  let state = documents.get(doc);
  const token = {};
  if (!state) {
    const initial = doc.body.getAttribute('data-scroll-locked');
    const count = initial !== null && /^\d+$/.test(initial) ? Number(initial) : 0;
    state = {
      doc, body: doc.body, view: doc.defaultView, leases: new Map(), styles: [],
      relinquished: new Set(), attributes: new Map(), scope: String(++nextScope),
      initialCount: Number.isSafeInteger(count) && count < Number.MAX_SAFE_INTEGER ? count : 0,
      style: null, css: '', styleChanged: false, resize: null,
    };
    state.leases.set(token, options);
    state.resize = () => refresh(state);
    try {
      state.style = doc.createElement('style');
      (doc.head || doc.documentElement).appendChild(state.style);
      refresh(state);
      state.view.addEventListener('resize', state.resize);
      documents.set(doc, state);
    } catch (error) {
      dispose(state);
      throw error;
    }
  } else {
    state.leases.set(token, options);
    try {
      refresh(state);
    } catch (error) {
      state.leases.delete(token);
      throw error;
    }
  }
  let released = false;
  return () => {
    if (released) return;
    released = true;
    state.leases.delete(token);
    if (state.leases.size) refresh(state);
    else dispose(state);
  };
}

export function RemoveScrollBar({ noRelative = false, noImportant = false, gapMode = 'margin' } = {}) {
  useClientEffect(() => {
    const doc = typeof document === 'undefined' ? null : document;
    if (!available(doc)) return undefined;
    return acquire(doc, { noRelative, noImportant, gapMode });
  }, [noRelative, noImportant, gapMode]);
  return null;
}
