import Icon from "./Icon";

export default function Pagination({ total, page, pageSize, onChange }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (total === 0) return null;

  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  return (
    <div className="pagination">
      <span className="pagination-info">
        {from}–{to} / {total}
      </span>
      <div className="pagination-controls">
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
        >
          <Icon name="arrowLeft" size={15} />
          Oldingi
        </button>
        <span className="pagination-page">
          {page} / {pages}
        </span>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          disabled={page >= pages}
          onClick={() => onChange(page + 1)}
        >
          Keyingi
          <Icon name="chevron" size={15} />
        </button>
      </div>
    </div>
  );
}
