import { useCallback, useEffect, useRef, useState } from "react";
import api, { apiError } from "../api";
import GrifBadge from "../components/GrifBadge";
import Icon from "../components/Icon";
import Modal from "../components/Modal";
import Pagination from "../components/Pagination";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../context/ToastContext";
import { BLACKLIST_STATUSES, PAGE_SIZE } from "../constants";
import { formatDate, ownerHandle } from "../utils";

function BlacklistDetailModal({ open, onClose, entry }) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Hodisa tafsilotlari"
      subtitle="Ruxsat etilmagan qurilma haqida ma'lumot"
      size="lg"
      footer={
        <button type="button" className="btn btn-ghost" onClick={onClose}>
          Yopish
        </button>
      }
    >
      {entry ? (
        <div className="detail-grid">
          <div className="detail-item">
            <span>Seriya raqami</span>
            <strong className="mono">{entry.serial_number}</strong>
          </div>
          <div className="detail-item">
            <span>Holat</span>
            <StatusBadge status={entry.status} />
          </div>
          <div className="detail-item">
            <span>Ishlab chiqaruvchi</span>
            <strong>{entry.vendor || "—"}</strong>
          </div>
          <div className="detail-item">
            <span>Model</span>
            <strong>{entry.model || "—"}</strong>
          </div>
          <div className="detail-item">
            <span>Qurilma turi</span>
            <strong>{entry.device_type || "—"}</strong>
          </div>
          <div className="detail-item">
            <span>Grif</span>
            <GrifBadge value={entry.grif} />
          </div>
          <div className="detail-item">
            <span>Egasi</span>
            <strong>{ownerHandle(entry.owner)}</strong>
          </div>
          <div className="detail-item">
            <span>Agent / kompyuter</span>
            <strong className="mono">{entry.agent_name || "—"}</strong>
          </div>
          <div className="detail-item">
            <span>Hodisalar soni</span>
            <strong>{entry.event_count}</strong>
          </div>
          <div className="detail-item">
            <span>Birinchi signal</span>
            <strong>{formatDate(entry.first_seen_at)}</strong>
          </div>
          <div className="detail-item">
            <span>Oxirgi signal</span>
            <strong>{formatDate(entry.last_seen_at)}</strong>
          </div>
          <div className="detail-item full">
            <span>Sabab / izoh</span>
            <strong className="detail-reason">{entry.reason || "—"}</strong>
          </div>
        </div>
      ) : null}
    </Modal>
  );
}

export default function Blacklist() {
  const { notify } = useToast();

  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: PAGE_SIZE });
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [ownerId, setOwnerId] = useState("");
  const [page, setPage] = useState(1);
  const [viewing, setViewing] = useState(null);
  const requestId = useRef(0);

  const canSeeOthers = users.length > 1;

  const load = useCallback(
    async (signal) => {
      const current = ++requestId.current;
      setLoading(true);
      try {
        const params = { page, page_size: PAGE_SIZE };
        if (search.trim()) params.search = search.trim();
        if (status) params.status = status;
        if (ownerId) params.owner_id = ownerId;
        const response = await api.get("/api/blacklist", { params, signal });
        if (current === requestId.current) setData(response.data);
      } catch (error) {
        if (error.name === "CanceledError" || error.code === "ERR_CANCELED") return;
        notify(apiError(error, "Qora ro'yxatni yuklab bo'lmadi"), "error");
      } finally {
        if (current === requestId.current) setLoading(false);
      }
    },
    [page, search, status, ownerId, notify]
  );

  const loadStats = useCallback(async () => {
    try {
      const response = await api.get("/api/stats");
      setStats(response.data);
    } catch {
      /* ixtiyoriy */
    }
  }, []);

  useEffect(() => {
    api
      .get("/api/users")
      .then(({ data: list }) => setUsers(list))
      .catch(() => setUsers([]));
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => load(controller.signal), 280);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [load]);

  useEffect(() => {
    const handler = () => {
      load();
      loadStats();
    };
    window.addEventListener("usbqalqon:blacklist-changed", handler);
    return () => window.removeEventListener("usbqalqon:blacklist-changed", handler);
  }, [load, loadStats]);

  function refresh() {
    load();
    loadStats();
  }

  async function openEntry(entry) {
    setViewing(entry);
    if (entry.status !== "yangi") return;

    try {
      const { data: reviewed } = await api.post(`/api/blacklist/${entry.id}/review`);
      setViewing(reviewed);
      setData((current) => ({
        ...current,
        items: current.items.map((item) => (item.id === reviewed.id ? reviewed : item)),
      }));
      loadStats();
      window.dispatchEvent(new Event("usbqalqon:blacklist-changed"));
      notify("Hodisa ko'rib chiqildi", "success");
    } catch (error) {
      notify(apiError(error, "Holatni yangilab bo'lmadi"), "error");
    }
  }

  async function handleDelete(entry) {
    if (!window.confirm(`"${entry.serial_number}" yozuvini o'chirmoqchimisiz?`)) return;
    try {
      await api.delete(`/api/blacklist/${entry.id}`);
      notify("Yozuv o'chirildi", "success");
      refresh();
    } catch (error) {
      notify(apiError(error, "Yozuvni o'chirib bo'lmadi"), "error");
    }
  }

  return (
    <div className="page page-danger">
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <Icon name="shield" size={15} />
            Xavfsizlik
          </span>
          <h2>Ruxsat etilmagan qurilmalar</h2>
          <p>
            Desktop agentlar tomonidan avtomatik aniqlangan va qora ro'yxatga
            yozilgan barcha qurilmalar. Har bir yangi hodisa administratorga
            bildirishnoma yuboradi.
          </p>
        </div>
        <div className="intro-stats">
          <div>
            <strong>{stats?.total_blacklist ?? "—"}</strong>
            <span>Jami</span>
          </div>
          <div>
            <strong className="text-danger">{stats?.new_blacklist ?? "—"}</strong>
            <span>Yangi</span>
          </div>
        </div>
      </section>

      <section className="panel panel-danger">
        <header className="panel-head">
          <div>
            <h2>Qora ro'yxat</h2>
            <p>Qidiruv, ko'rish va o'chirish. Yozuvlar agentlar tomonidan qo'shiladi.</p>
          </div>
          <span className="badge badge-danger">
            <span className="status-dot" />
            Xavfli hudud
          </span>
        </header>

        <div className="toolbar">
          <div className="search-box">
            <Icon name="search" size={17} />
            <input
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
              placeholder="Seriya, model, sabab, agent, egasi..."
            />
            {search ? (
              <button
                type="button"
                className="input-action"
                onClick={() => {
                  setSearch("");
                  setPage(1);
                }}
                aria-label="Qidiruvni tozalash"
              >
                <Icon name="close" size={15} />
              </button>
            ) : null}
          </div>

          <select
            className="filter-select"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setPage(1);
            }}
          >
            <option value="">Barcha holatlar</option>
            {BLACKLIST_STATUSES.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>

          {canSeeOthers ? (
            <select
              className="filter-select"
              value={ownerId}
              onChange={(event) => {
                setOwnerId(event.target.value);
                setPage(1);
              }}
            >
              <option value="">Barcha bo'limlar</option>
              {users.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.full_name || item.username}
                </option>
              ))}
            </select>
          ) : null}

          <span className="toolbar-count">
            <b>{data.total}</b> ta natija
          </span>
        </div>

        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th className="col-num">№</th>
                <th>Seriya raqami</th>
                <th>Qurilma</th>
                <th>Grif</th>
                <th>Sabab</th>
                <th>Egasi</th>
                <th className="text-center">Hodisalar</th>
                <th>Oxirgi signal</th>
                <th>Holat</th>
                <th className="col-actions">Amallar</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={10} className="table-state">
                    <span className="spinner spinner-sm" />
                    Yuklanmoqda...
                  </td>
                </tr>
              ) : data.items.length === 0 ? (
                <tr>
                  <td colSpan={10} className="table-state">
                    <Icon name="shield" size={22} />
                    <strong>Yozuvlar topilmadi</strong>
                    <span>Agentlar hali signal yubormagan bo'lishi mumkin</span>
                  </td>
                </tr>
              ) : (
                data.items.map((entry, index) => (
                  <tr
                    key={entry.id}
                    className="row-clickable"
                    onClick={() => openEntry(entry)}
                    title="Tafsilotlarni ko'rish"
                  >
                    <td className="col-num muted">
                      {(data.page - 1) * data.page_size + index + 1}
                    </td>
                    <td>
                      <span className="mono">{entry.serial_number}</span>
                    </td>
                    <td>
                      <div className="stacked">
                        <span>{entry.vendor || "—"}</span>
                        <small className="muted">{entry.model || "Model yo'q"}</small>
                        <span className="type-chip">{entry.device_type}</span>
                      </div>
                    </td>
                    <td>
                      <GrifBadge value={entry.grif} />
                    </td>
                    <td className="cell-wrap">{entry.reason || <span className="muted">—</span>}</td>
                    <td className="mono">{ownerHandle(entry.owner)}</td>
                    <td className="text-center">
                      <span className="count-pill">{entry.event_count}</span>
                    </td>
                    <td className="nowrap muted">{formatDate(entry.last_seen_at)}</td>
                    <td>
                      <StatusBadge status={entry.status} />
                    </td>
                    <td className="col-actions">
                      <div className="row-actions">
                        <button
                          type="button"
                          className="icon-btn icon-btn-danger"
                          title="O'chirish"
                          onClick={(event) => {
                            event.stopPropagation();
                            handleDelete(entry);
                          }}
                        >
                          <Icon name="trash" size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <Pagination
          total={data.total}
          page={page}
          pageSize={PAGE_SIZE}
          onChange={setPage}
        />
      </section>

      <BlacklistDetailModal
        open={Boolean(viewing)}
        onClose={() => setViewing(null)}
        entry={viewing}
      />
    </div>
  );
}
