import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import api, { apiError } from "../api";
import GrifBadge from "../components/GrifBadge";
import Icon from "../components/Icon";
import Modal from "../components/Modal";
import Pagination from "../components/Pagination";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import {
  DEVICE_TYPES,
  GRIFS,
  PAGE_SIZE,
} from "../constants";
import { downloadBlob, formatDate, ownerHandle } from "../utils";

const EMPTY_FORM = {
  serial_number: "",
  vendor: "",
  model: "",
  grif: "Nomaxfiy",
  device_type: "Fleshka",
  owner_id: "",
};

function StatCard({ icon, tone, label, value, hint }) {
  return (
    <div className="stat-card">
      <span className={`stat-icon tone-${tone}`}>
        <Icon name={icon} size={22} />
      </span>
      <div>
        <span className="stat-label">{label}</span>
        <strong className="stat-value">{value ?? "—"}</strong>
        <span className="stat-hint">{hint}</span>
      </div>
    </div>
  );
}

function DeviceFormModal({ open, onClose, device, users, currentUser, onSaved }) {
  const { notify } = useToast();
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (device) {
      setForm({
        serial_number: device.serial_number || "",
        vendor: device.vendor || "",
        model: device.model || "",
        grif: device.grif || "Nomaxfiy",
        device_type: device.device_type || "USB qurilma",
        owner_id: device.owner_id || "",
      });
    } else {
      setForm({ ...EMPTY_FORM, owner_id: currentUser?.id || "" });
    }
  }, [open, device, currentUser]);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    try {
      const payload = {
        serial_number: form.serial_number.trim(),
        vendor: form.vendor.trim(),
        model: form.model.trim(),
        grif: form.grif,
        device_type: form.device_type,
        owner_id: form.owner_id ? Number(form.owner_id) : null,
      };

      if (device) {
        await api.put(`/api/devices/${device.id}`, payload);
        notify("Qurilma yangilandi", "success");
      } else {
        await api.post("/api/devices", payload);
        notify("Yangi qurilma qo'shildi", "success");
      }
      onSaved?.();
      onClose();
    } catch (error) {
      notify(apiError(error, "Qurilmani saqlab bo'lmadi"), "error");
    } finally {
      setSaving(false);
    }
  }

  const canChooseOwner = users.length > 1;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={device ? "Qurilmani tahrirlash" : "Yangi qurilma"}
      subtitle="Devices.txt formatidagi maydonlar"
      footer={
        <>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Bekor qilish
          </button>
          <button
            type="submit"
            form="device-form"
            className="btn btn-primary"
            disabled={saving}
          >
            {saving ? "Saqlanmoqda..." : "Saqlash"}
          </button>
        </>
      }
    >
      <form id="device-form" className="form-grid" onSubmit={handleSubmit}>
        <label className="field field-full">
          <span>Seriya raqami *</span>
          <input
            value={form.serial_number}
            onChange={(event) => update("serial_number", event.target.value)}
            placeholder="E0D55E6C382BE820D9430146"
            required
            maxLength={255}
          />
        </label>
        <label className="field">
          <span>Ishlab chiqaruvchi</span>
          <input
            value={form.vendor}
            onChange={(event) => update("vendor", event.target.value)}
            placeholder="KINGSTON"
            maxLength={160}
          />
        </label>
        <label className="field">
          <span>Model</span>
          <input
            value={form.model}
            onChange={(event) => update("model", event.target.value)}
            placeholder="DATATRAVELER_3.0"
            maxLength={200}
          />
        </label>
        <label className="field">
          <span>Grif</span>
          <select value={form.grif} onChange={(event) => update("grif", event.target.value)}>
            {GRIFS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Qurilma turi</span>
          <select
            value={form.device_type}
            onChange={(event) => update("device_type", event.target.value)}
          >
            {DEVICE_TYPES.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        {canChooseOwner ? (
          <label className="field field-full">
            <span>Bo'lim (egasi)</span>
            <select
              value={form.owner_id}
              onChange={(event) => update("owner_id", event.target.value)}
            >
              {users.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.full_name || item.username} (@{item.username})
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </form>
    </Modal>
  );
}

function ImportModal({ open, onClose, users, currentUser, onImported }) {
  const { notify } = useToast();
  const [file, setFile] = useState(null);
  const [ownerId, setOwnerId] = useState("");
  const [result, setResult] = useState(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setFile(null);
    setResult(null);
    setOwnerId(String(currentUser?.id || ""));
  }, [open, currentUser]);

  async function handleUpload(event) {
    event.preventDefault();
    if (!file) {
      notify("Avval Devices.txt faylini tanlang", "error");
      return;
    }

    const data = new FormData();
    data.append("file", file);
    if (ownerId) data.append("owner_id", ownerId);

    setUploading(true);
    try {
      const response = await api.post("/api/devices/import", data, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(response.data);
      notify(
        `${response.data.imported} ta qurilma import qilindi, ${response.data.skipped} ta o'tkazib yuborildi`,
        "success"
      );
      onImported?.();
    } catch (error) {
      notify(apiError(error, "Faylni import qilib bo'lmadi"), "error");
    } finally {
      setUploading(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Devices.txt import"
      subtitle="Desktop dastur formatidagi faylni yuklang"
      footer={
        <>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Yopish
          </button>
          <button
            type="submit"
            form="import-form"
            className="btn btn-primary"
            disabled={uploading || !file}
          >
            {uploading ? "Yuklanmoqda..." : "Import qilish"}
          </button>
        </>
      }
    >
      <form id="import-form" className="form-grid" onSubmit={handleUpload}>
        <label className="dropzone field-full">
          <Icon name="upload" size={28} />
          <strong>{file ? file.name : "Faylni tanlang yoki bu yerga tashlang"}</strong>
          <small>Qo'llab-quvvatlanadi: .txt (UTF-8 yoki CP1251), 10 MB gacha</small>
          <input
            type="file"
            accept=".txt,text/plain"
            onChange={(event) => {
              setFile(event.target.files?.[0] || null);
              setResult(null);
            }}
          />
        </label>

        {users.length > 1 ? (
          <label className="field field-full">
            <span>Qaysi bo'limga import qilinsin?</span>
            <select value={ownerId} onChange={(event) => setOwnerId(event.target.value)}>
              {users.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.full_name || item.username} (@{item.username})
                </option>
              ))}
            </select>
          </label>
        ) : null}

        {result ? (
          <div className="import-result field-full">
            <div className="import-result-head">
              <Icon name="check" size={18} />
              <strong>Import yakunlandi</strong>
            </div>
            <div className="import-result-grid">
              <span>
                <b>{result.total_records}</b> yozuv
              </span>
              <span className="text-success">
                <b>{result.imported}</b> qo'shildi
              </span>
              <span className="text-danger">
                <b>{result.skipped}</b> o'tkazildi
              </span>
            </div>
            {result.errors?.length ? (
              <ul className="import-errors">
                {result.errors.slice(0, 8).map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}

        <div className="format-hint field-full">
          <strong>Kutilayotgan format:</strong>
          <code>
            Seriya raqami: E0D55E6C...; Ishlab chiqaruvchi: KINGSTON; Model:
            DATATRAVELER_3.0; Grif: Nomaxfiy
          </code>
        </div>
      </form>
    </Modal>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const { notify } = useToast();

  const [devices, setDevices] = useState({ items: [], total: 0, page: 1, page_size: PAGE_SIZE });
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [grif, setGrif] = useState("");
  const [ownerId, setOwnerId] = useState("");
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [importOpen, setImportOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const requestId = useRef(0);

  const canSeeOthers = users.length > 1;

  const loadDevices = useCallback(
    async (signal) => {
      const currentRequest = ++requestId.current;
      setLoading(true);
      try {
        const params = { page, page_size: PAGE_SIZE };
        if (search.trim()) params.search = search.trim();
        if (grif) params.grif = grif;
        if (ownerId) params.owner_id = ownerId;

        const { data } = await api.get("/api/devices", { params, signal });
        if (currentRequest === requestId.current) setDevices(data);
      } catch (error) {
        if (error.name === "CanceledError" || error.code === "ERR_CANCELED") return;
        notify(apiError(error, "Qurilmalarni yuklab bo'lmadi"), "error");
      } finally {
        if (currentRequest === requestId.current) setLoading(false);
      }
    },
    [page, search, grif, ownerId, notify]
  );

  const loadStats = useCallback(async () => {
    try {
      const { data } = await api.get("/api/stats");
      setStats(data);
    } catch {
      /* statistika ixtiyoriy */
    }
  }, []);

  useEffect(() => {
    api
      .get("/api/users")
      .then(({ data }) => setUsers(data))
      .catch(() => setUsers([]));
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => loadDevices(controller.signal), 280);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [loadDevices]);

  function refresh() {
    loadDevices();
    loadStats();
  }

  function resetFilters() {
    setSearch("");
    setGrif("");
    setOwnerId("");
    setPage(1);
  }

  async function handleDelete(device) {
    if (!window.confirm(`"${device.serial_number}" qurilmasini o'chirmoqchimisiz?`)) return;
    try {
      await api.delete(`/api/devices/${device.id}`);
      notify("Qurilma o'chirildi", "success");
      refresh();
    } catch (error) {
      notify(apiError(error, "Qurilmani o'chirib bo'lmadi"), "error");
    }
  }

  async function handleExport() {
    setExporting(true);
    try {
      const response = await api.get("/api/devices/export", { responseType: "blob" });
      downloadBlob(response.data, "Devices.txt");
      notify("Devices.txt yuklab olindi", "success");
    } catch (error) {
      notify(apiError(error, "Eksport qilib bo'lmadi"), "error");
    } finally {
      setExporting(false);
    }
  }

  const grifEntries = useMemo(
    () => Object.entries(stats?.grif_breakdown || {}).sort((a, b) => b[1] - a[1]),
    [stats]
  );

  return (
    <div className="page page-success">
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <Icon name="check" size={15} />
            Ruxsat etilgan baza
          </span>
          <h2>Ro'yxatdan o'tgan qurilmalar</h2>
          <p>
            Bo'limlarga tegishli barcha ruxsat etilgan USB qurilmalar. Ushbu
            bazadagi qurilmalar desktop agent tomonidan bloklanmaydi.
          </p>
        </div>
        <div className="intro-stats">
          <div>
            <strong>{stats?.total_devices ?? "—"}</strong>
            <span>Qurilmalar</span>
          </div>
          <div>
            <strong>{stats?.total_users ?? "—"}</strong>
            <span>Bo'limlar</span>
          </div>
        </div>
      </section>

      <section className="stat-grid">
        <StatCard
          icon="database"
          tone="blue"
          label="Jami qurilmalar"
          value={stats?.total_devices}
          hint="Ruxsat etilgan baza"
        />
        <StatCard
          icon="shield"
          tone="red"
          label="Qora ro'yxat"
          value={stats?.total_blacklist}
          hint="Ruxsat etilmagan qurilmalar"
        />
        <StatCard
          icon="users"
          tone="violet"
          label="Foydalanuvchilar"
          value={stats?.total_users}
          hint="Ko'rinadigan bo'limlar"
        />
        <StatCard
          icon="alert"
          tone="amber"
          label="Yangi hodisalar"
          value={stats?.new_blacklist}
          hint="Ko'rib chiqilmagan"
        />
      </section>

      <section className="panel panel-success">
        <header className="panel-head">
          <div>
            <h2>Qurilmalar bazasi</h2>
            <p>Barcha ruxsat etilgan USB qurilmalar ro'yxati</p>
          </div>
          <div className="panel-actions">
            <button
              type="button"
              className="btn btn-ghost"
              onClick={handleExport}
              disabled={exporting}
            >
              <Icon name="download" size={16} />
              {exporting ? "Yuklanmoqda..." : "Export"}
            </button>
            <button type="button" className="btn btn-ghost" onClick={() => setImportOpen(true)}>
              <Icon name="upload" size={16} />
              Import
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                setEditing(null);
                setFormOpen(true);
              }}
            >
              <Icon name="plus" size={16} />
              Qurilma qo'shish
            </button>
          </div>
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
              placeholder="Seriya, ishlab chiqaruvchi, model, grif, egasi..."
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
            value={grif}
            onChange={(event) => {
              setGrif(event.target.value);
              setPage(1);
            }}
          >
            <option value="">Barcha griflar</option>
            {GRIFS.map((item) => (
              <option key={item} value={item}>
                {item}
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

          {search || grif || ownerId ? (
            <button type="button" className="btn btn-ghost btn-sm" onClick={resetFilters}>
              <Icon name="refresh" size={14} />
              Tozalash
            </button>
          ) : null}

          <span className="toolbar-count">
            <b>{devices.total}</b> ta natija
          </span>
        </div>

        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th className="col-num">№</th>
                <th>Seriya raqami</th>
                <th>Ishlab chiqaruvchi</th>
                <th>Model</th>
                <th>Turi</th>
                <th>Grif</th>
                {canSeeOthers ? <th>Egasi</th> : null}
                <th>Sana</th>
                <th className="col-actions">Amallar</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={canSeeOthers ? 9 : 8} className="table-state">
                    <span className="spinner spinner-sm" />
                    Yuklanmoqda...
                  </td>
                </tr>
              ) : devices.items.length === 0 ? (
                <tr>
                  <td colSpan={canSeeOthers ? 9 : 8} className="table-state">
                    <Icon name="search" size={22} />
                    <strong>Qurilma topilmadi</strong>
                    <span>Qidiruvni o'zgartiring yoki yangi qurilma qo'shing</span>
                  </td>
                </tr>
              ) : (
                devices.items.map((device, index) => (
                  <tr key={device.id}>
                    <td className="col-num muted">
                      {(devices.page - 1) * devices.page_size + index + 1}
                    </td>
                    <td>
                      <span className="mono">{device.serial_number}</span>
                    </td>
                    <td>{device.vendor || <span className="muted">—</span>}</td>
                    <td>{device.model || <span className="muted">—</span>}</td>
                    <td>
                      <span className="type-chip">{device.device_type}</span>
                    </td>
                    <td>
                      <GrifBadge value={device.grif} />
                    </td>
                    {canSeeOthers ? (
                      <td>
                        <span className="owner-cell mono">
                          {ownerHandle(device.owner)}
                        </span>
                      </td>
                    ) : null}
                    <td className="nowrap muted">{formatDate(device.created_at)}</td>
                    <td className="col-actions">
                      <div className="row-actions">
                        <button
                          type="button"
                          className="icon-btn"
                          title="Tahrirlash"
                          onClick={() => {
                            setEditing(device);
                            setFormOpen(true);
                          }}
                        >
                          <Icon name="edit" size={16} />
                        </button>
                        <button
                          type="button"
                          className="icon-btn icon-btn-danger"
                          title="O'chirish"
                          onClick={() => handleDelete(device)}
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
          total={devices.total}
          page={page}
          pageSize={PAGE_SIZE}
          onChange={setPage}
        />
      </section>

      <section className="split-grid">
        <div className="panel">
          <header className="panel-head compact">
            <div>
              <h2>Griflar kesimi</h2>
              <p>Qurilmalarning maxfiylik darajasi</p>
            </div>
          </header>
          <div className="grif-breakdown">
            {grifEntries.length === 0 ? (
              <p className="muted">Ma'lumot yo'q</p>
            ) : (
              grifEntries.map(([name, count]) => {
                const total = stats?.total_devices || 1;
                const percent = Math.round((count / total) * 100);
                return (
                  <div className="grif-row" key={name}>
                    <div className="grif-row-head">
                      <GrifBadge value={name} />
                      <span>
                        <b>{count}</b> ta · {percent}%
                      </span>
                    </div>
                    <div className="bar">
                      <span style={{ width: `${percent}%` }} />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="panel">
          <header className="panel-head compact">
            <div>
              <h2>So'nggi hodisalar</h2>
              <p>Qora ro'yxatdagi oxirgi qurilmalar</p>
            </div>
            <span className="badge badge-neutral">{stats?.total_blacklist ?? 0}</span>
          </header>
          <div className="event-list">
            {stats?.recent_blacklist?.length ? (
              stats.recent_blacklist.map((entry) => (
                <div className="event-item" key={entry.id}>
                  <span className="event-icon">
                    <Icon name="shield" size={17} />
                  </span>
                  <div className="event-main">
                    <strong className="mono">{entry.serial_number}</strong>
                    <small>
                      {ownerHandle(entry.owner)} · {formatDate(entry.last_seen_at)}
                    </small>
                  </div>
                  <StatusBadge status={entry.status} />
                </div>
              ))
            ) : (
              <p className="muted">Hozircha hodisalar yo'q</p>
            )}
          </div>
        </div>
      </section>

      <DeviceFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        device={editing}
        users={users}
        currentUser={user}
        onSaved={refresh}
      />
      <ImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        users={users}
        currentUser={user}
        onImported={refresh}
      />
    </div>
  );
}
