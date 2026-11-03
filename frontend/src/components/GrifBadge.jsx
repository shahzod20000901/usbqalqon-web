import { GRIF_CLASS } from "../constants";

export default function GrifBadge({ value }) {
  if (!value) return <span className="muted">—</span>;
  return (
    <span className={`badge ${GRIF_CLASS[value] || "grif-0"}`}>{value}</span>
  );
}
