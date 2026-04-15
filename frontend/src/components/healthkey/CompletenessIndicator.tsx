/**
 * CompletenessIndicator — circular SVG progress ring.
 * Per docs/patient-app-design.md §4.2.
 *
 * - Color shifts: red < 30%, amber 30–70%, green > 70%
 * - Shown at 64px default; pass `size` for variants
 * - Center label + supporting label below
 */
interface Props {
  value: number; // 0–100
  size?: number;
  label?: string;
}

export function CompletenessIndicator({ value, size = 64, label }: Props) {
  const stroke = 6;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  const colorClass =
    value < 30 ? "text-error-700" : value < 70 ? "text-warning-700" : "text-success-700";

  return (
    <div className="inline-flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={stroke}
            fill="none"
            className="text-muted"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={stroke}
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className={`transition-all duration-500 ${colorClass}`}
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
          />
        </svg>
        <div
          className="absolute inset-0 flex items-center justify-center text-h4 font-bold text-foreground"
          aria-live="polite"
        >
          {Math.round(value)}%
        </div>
      </div>
      {label && <p className="text-caption text-muted-foreground">{label}</p>}
    </div>
  );
}
