/** Already-qualified display text. Feature owners retain facts and context. */
export interface DetailRow {
  readonly label: string;
  readonly value: string;
}

/** The passive fields used by the read-only currency provenance pilot. */
export interface NoticeView {
  readonly id: string;
  readonly title: string;
  readonly presentation: 'information' | 'warning';
  readonly cause: string;
  readonly impact: string;
  readonly automatic: string;
  readonly userNeed: string;
  readonly details: readonly DetailRow[];
  readonly action: {
    readonly label: string;
    readonly href: string;
  };
}

export interface NoticeCardProps {
  readonly notice: NoticeView;
  readonly headingLevel: 2 | 3 | 4;
  readonly detailsId: string;
}
