const LABELS = {
  yangi: "Yangi",
  korildi: "Ko'rib chiqildi",
  bloklandi: "Bloklandi",
};

export default function StatusBadge({ status }) {
  return (
    <span className={`status status-${status || "yangi"}`}>
      <span className="status-dot" />
      {LABELS[status] || status}
    </span>
  );
}
