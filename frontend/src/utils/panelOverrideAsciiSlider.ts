/**
 * ASCII override slider segment coloring — mirrors {@link VerticalSlider}
 * and {@link RapidTraverseSlider} in `PanelPane.tsx` (feed/spindle + rapid).
 */

export type OverrideSliderTone = 'grey' | 'green' | 'yellow' | 'orange' | 'red';

export interface HorizontalFeedSpindleSliderModel {
  filledSegments: number;
  displayValue: string;
  valueBoxTone: OverrideSliderTone;
  /** Index 0 = left (segment 1), length `segments`. */
  segmentTones: OverrideSliderTone[];
  segmentFilled: boolean[];
}

export interface HorizontalRapidSliderModel {
  filledSegments: number;
  displayValue: string;
  valueBoxTone: OverrideSliderTone;
  segmentTones: OverrideSliderTone[];
  segmentFilled: boolean[];
}

const SEGMENTS = 20;
const SEGMENT_SIZE = 10;

/** Feed / spindle override (0–200%, 999 = prohibited) — same math as PanelPane VerticalSlider. */
export function computeHorizontalFeedSpindleSlider(value: number, segments = SEGMENTS): HorizontalFeedSpindleSliderModel {
  const isProhibited = value === 999;
  const percentage = value;
  const isExact100 = percentage === 100;
  const isOver100 = percentage > 100;
  const segmentsPer100 = segments / 2;
  const filledSegments = isProhibited ? 0 : Math.min(Math.ceil(percentage / SEGMENT_SIZE), segments);

  let valueBoxTone: OverrideSliderTone = 'grey';
  if (isProhibited) {
    valueBoxTone = 'red';
  } else if (filledSegments > segmentsPer100) {
    valueBoxTone = 'red';
  } else if (filledSegments === segmentsPer100) {
    valueBoxTone = 'green';
  } else if (filledSegments >= segmentsPer100 * 0.75) {
    valueBoxTone = 'yellow';
  } else if (filledSegments >= segmentsPer100 * 0.5) {
    valueBoxTone = 'orange';
  } else {
    valueBoxTone = 'grey';
  }

  const displayValue = isProhibited ? 'XXX' : value.toString().padStart(3, '0');

  const segmentFilled: boolean[] = [];
  const segmentTones: OverrideSliderTone[] = [];

  for (let segmentNum = 1; segmentNum <= segments; segmentNum++) {
    const isFilled = segmentNum <= filledSegments;
    segmentFilled.push(isFilled);

    let segmentColor: OverrideSliderTone = 'grey';
    if (isFilled) {
      if (segmentNum <= segmentsPer100) {
        if (isExact100) {
          segmentColor = 'green';
        } else if (isOver100) {
          segmentColor = 'green';
        } else {
          const filledInRange = Math.min(filledSegments, segmentsPer100);
          if (filledInRange === segmentsPer100) {
            segmentColor = 'green';
          } else if (filledInRange >= segmentsPer100 * 0.75) {
            segmentColor = 'yellow';
          } else if (filledInRange >= segmentsPer100 * 0.5) {
            segmentColor = 'orange';
          } else {
            segmentColor = 'grey';
          }
        }
      } else {
        segmentColor = 'red';
      }
    }

    segmentTones.push(segmentColor);
  }

  return {
    filledSegments,
    displayValue,
    valueBoxTone,
    segmentTones,
    segmentFilled,
  };
}

/** Rapid traverse discrete override — same mapping as PanelPane RapidTraverseSlider. */
export function computeHorizontalRapidSlider(value: number, segments = SEGMENTS): HorizontalRapidSliderModel {
  const isProhibited = value === 9;

  let displayValue: string;
  let filledSegments = 0;

  if (isProhibited) {
    displayValue = 'XXX';
    filledSegments = 0;
  } else if (value === 0 || value === 5) {
    displayValue = '000';
    filledSegments = 0;
  } else if (value === 1) {
    displayValue = '001';
    filledSegments = 5;
  } else if (value === 2) {
    displayValue = '002';
    filledSegments = 10;
  } else if (value === 3) {
    displayValue = '003';
    filledSegments = 15;
  } else if (value === 4) {
    displayValue = '100';
    filledSegments = 20;
  } else {
    displayValue = '000';
    filledSegments = 0;
  }

  let valueBoxTone: OverrideSliderTone = 'grey';
  if (isProhibited) {
    valueBoxTone = 'red';
  } else if (filledSegments === segments) {
    valueBoxTone = 'green';
  } else if (filledSegments >= segments * 0.75) {
    valueBoxTone = 'yellow';
  } else if (filledSegments >= segments * 0.5) {
    valueBoxTone = 'orange';
  } else {
    valueBoxTone = 'grey';
  }

  const segmentFilled: boolean[] = [];
  const segmentTones: OverrideSliderTone[] = [];

  for (let segmentNum = 1; segmentNum <= segments; segmentNum++) {
    const isFilled = segmentNum <= filledSegments;
    segmentFilled.push(isFilled);

    let segmentColor: OverrideSliderTone = 'grey';
    if (isFilled) {
      if (filledSegments === segments) {
        segmentColor = 'green';
      } else if (filledSegments >= segments * 0.75) {
        segmentColor = 'yellow';
      } else if (filledSegments >= segments * 0.5) {
        segmentColor = 'orange';
      } else {
        segmentColor = 'grey';
      }
    }

    segmentTones.push(segmentColor);
  }

  return {
    filledSegments,
    displayValue,
    valueBoxTone,
    segmentTones,
    segmentFilled,
  };
}
