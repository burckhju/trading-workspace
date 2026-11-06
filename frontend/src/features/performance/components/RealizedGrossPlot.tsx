import {
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  XAxis,
  YAxis,
} from 'recharts';

export interface SellPlotEntry {
  ordinal: number;
  executionId: string;
  value: number;
}

function ContributionMark({
  cx,
  cy,
  payload,
}: {
  cx?: number;
  cy?: number;
  payload?: SellPlotEntry;
}) {
  return (
    <circle
      cx={cx}
      cy={cy}
      r={5}
      fill="#7dd3fc"
      stroke="#020617"
      strokeWidth={1.5}
      data-testid="sell-contribution-mark"
      data-execution-id={payload?.executionId}
    />
  );
}

/** Categorical events, not a time series. The adjacent table is the full alternative. */
export function RealizedGrossPlot({
  entries,
  ordinals,
  extent,
}: {
  entries: SellPlotEntry[];
  ordinals: number[];
  extent: number;
}) {
  return (
    <div
      aria-hidden="true"
      className="min-w-0"
      style={{ height: Math.max(190, ordinals.length * 32 + 60) }}
    >
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <ScatterChart
          margin={{ top: 12, right: 22, bottom: 12, left: 0 }}
          accessibilityLayer={false}
        >
          <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
          <XAxis
            type="number"
            dataKey="value"
            domain={[-extent, extent]}
            tickCount={3}
            tick={{ fill: '#cbd5e1', fontSize: 12 }}
            tickFormatter={(value: number) =>
              new Intl.NumberFormat('de-DE', {
                maximumSignificantDigits: 3,
                notation:
                  Math.abs(value) >= 1e6 || (value !== 0 && Math.abs(value) < 0.001)
                    ? 'scientific'
                    : 'standard',
              }).format(value)
            }
            allowDataOverflow
          />
          <YAxis
            type="number"
            dataKey="ordinal"
            domain={[ordinals[0] - 0.5, ordinals[ordinals.length - 1] + 0.5]}
            ticks={ordinals}
            tickFormatter={(value: number) => `SELL ${value}`}
            tick={{ fill: '#cbd5e1', fontSize: 12 }}
            width={65}
            interval={0}
            reversed
            allowDataOverflow
          />
          <ReferenceLine x={0} stroke="#cbd5e1" />
          <Scatter data={entries} shape={<ContributionMark />} isAnimationActive={false} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
