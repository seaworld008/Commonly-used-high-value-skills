/** Original runtime for the six documented exports; no other package API is implied. */
export interface RemoveScrollBarProps {
  /** Keep the body's existing position (default: make a static body relative). */
  noRelative?: boolean;
  /** Omit !important on owned inline styles and class rules (default: false). */
  noImportant?: boolean;
  /** Add the removed gutter to this physical edge spacing (default: margin). */
  gapMode?: 'padding' | 'margin';
}

/** Renders null. The earliest active instance in each Document selects options. */
export declare function RemoveScrollBar(props?: RemoveScrollBarProps): null;

/** Current computed physical offsets and nonnegative viewport gutter; SSR returns zeros. */
export declare function getGapWidth(gapMode?: 'padding' | 'margin'): {
  left: number;
  top: number;
  right: number;
  gap: number;
};

export declare const zeroRightClassName: 'right-scroll-bar-position';
export declare const fullWidthClassName: 'width-before-scroll-bar';
export declare const noScrollbarsClassName: 'with-scroll-bars-hidden';
export declare const removedBarSizeVariable: '--removed-body-scroll-bar-size';
