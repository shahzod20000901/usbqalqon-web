import { useCallback, useEffect, useMemo, useState } from "react";
import api, { apiError } from "../api";
import Icon from "../components/Icon";
import Modal from "../components/Modal";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { ROLES } from "../constants";
import { formatDateOnly, initials } from "../utils";

const ROLE_LABEL = Object.fromEntries(ROLES.map((item) => [item.value, item.label]));
const ROLE_CLASS = {
  admin: "role-admin",
  rahbar: "role-rahbar",
  xodim: "role-xodim",
};

function RoleBadge({ role }) {
  return (
    <span className={`role-badge ${ROLE_CLASS[role] || "role-xodim"}`}>
      {ROLE_LABEL[role] || role || "Xodim"}
    </span>
  );
}

function UserFormModal({
  open,
  onClose,
  user,
  currentUser,
  allUsers,
  presetParentId,
  onSaved,
}) {
  const { notify } = useToast();
  const [form, setForm] = useState({
    username: "",
    full_name: "",
    password: "",
    role: "xodim",
    parent_id: "",
    is_active: true,
    is_superuser: false,
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (user) {
      setForm({
        username: user.username || "",
        full_name: user.full_name || "",
        password: "",
        role: user.role || "xodim",
        parent_id: user.parent_id ?? "",
        is_active: user.is_active !== false,
        is_superuser: Boolean(user.is_superuser),
      });
    } else {
      const defaultParent = presetParentId ?? currentUser?.id ?? "";
      setForm({
        username: "",
        full_name: "",
        password: "",
        role: "xodim",
        parent_id: defaultParent === null ? "" : String(defaultParent),
        is_active: true,
        is_superuser: false,
      });
    }
  }, [open, user, currentUser, presetParentId]);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    try {
      const payload = {
        username: form.username.trim(),
        full_name: form.full_name.trim(),
        role: form.role,
        is_active: form.is_active,
      };

      if (currentUser?.is_superuser) {
        payload.is_superuser = form.is_superuser;
      }

      if (form.parent_id === "") {
        payload.parent_id = null;
      } else {
        payload.parent_id = Number(form.parent_id);
      }

      if (form.password) {
        payload.password = form.password;
      }

      if (user) {
        await api.put(`/api/users/${user.id}`, payload);
        notify("Foydalanuvchi yangilandi", "success");
      } else {
        await api.post("/api/users", payload);
        notify("Foydalanuvchi qo'shildi", "success");
      }

      onSaved?.();
      onClose();
    } catch (error) {
      notify(apiError(error, "Foydalanuvchini saqlab bo'lmadi"), "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={user ? "Foydalanuvchini tahrirlash" : "Yangi foydalanuvchi"}
      subtitle="Tashkiliy tuzilmadagi o'rni va rolini belgilang"
      size="lg"
      footer={
        <>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Bekor qilish
          </button>
          <button
            type="submit"
            form="user-form"
            className="btn btn-primary"
            disabled={saving}
          >
            {saving ? "Saqlanmoqda..." : "Saqlash"}
          </button>
        </>
      }
    >
      <form id="user-form" className="form-grid" onSubmit={handleSubmit}>
        <label className="field">
          <span>Login *</span>
          <input
            value={form.username}
            onChange={(event) => update("username", event.target.value)}
            placeholder="xodim.ism"
            required
            minLength={3}
            maxLength={64}
            pattern="[A-Za-z0-9_.-]+"
            title="Faqat lotin harflari, raqamlar, _ . - belgilari"
          />
        </label>
        <label className="field">
          <span>F.I.Sh</span>
          <input
            value={form.full_name}
            onChange={(event) => update("full_name", event.target.value)}
            placeholder="Ism Familiya"
            maxLength={160}
          />
        </label>
        <label className="field">
          <span>{user ? "Yangi parol" : "Parol *"}</span>
          <input
            type="password"
            value={form.password}
            onChange={(event) => update("password", event.target.value)}
            placeholder={user ? "O'zgartirmaslik uchun bo'sh qoldiring" : "Kamida 4 belgi"}
            required={!user}
            minLength={4}
            autoComplete="new-password"
          />
        </label>
        <label className="field">
          <span>Rol</span>
          <select value={form.role} onChange={(event) => update("role", event.target.value)}>
            {ROLES.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field field-full">
          <span>Yuqori bo'lim</span>
          <select
            value={form.parent_id}
            onChange={(event) => update("parent_id", event.target.value)}
          >
            {currentUser?.is_superuser ? <option value="">— Ildiz bo'lim —</option> : null}
            {allUsers
              .filter((item) => !user || item.id !== user.id)
              .map((item) => (
                <option key={item.id} value={item.id}>
                  {item.full_name || item.username} (@{item.username})
                </option>
              ))}
          </select>
        </label>
        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(event) => update("is_active", event.target.checked)}
          />
          <span>Faol foydalanuvchi</span>
        </label>
        {currentUser?.is_superuser ? (
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={form.is_superuser}
              onChange={(event) => update("is_superuser", event.target.checked)}
            />
            <span>Administrator huquqi</span>
          </label>
        ) : null}
      </form>
    </Modal>
  );
}

function TreeNode({ node, level, expanded, toggle, onAdd, onEdit, onDelete, currentUser }) {
  const hasChildren = Boolean(node.children?.length);
  const open = expanded[node.id] !== false;
  const isSelf = node.id === currentUser?.id;

  return (
    <div className="tree-node">
      <div className="tree-row" style={{ paddingLeft: 14 + level * 22 }}>
        <button
          type="button"
          className={`tree-toggle ${hasChildren ? "" : "tree-toggle-empty"}`}
          onClick={() => hasChildren && toggle(node.id)}
          aria-label={open ? "Yig'ish" : "Ochish"}
          disabled={!hasChildren}
        >
          {hasChildren ? <Icon name={open ? "chevronDown" : "chevron"} size={15} /> : null}
        </button>

        <span className="avatar avatar-sm">{initials(node.full_name, node.username?.[0])}</span>

        <div className="tree-user">
          <strong>
            {node.full_name || node.username}
            {isSelf ? <span className="self-mark">siz</span> : null}
          </strong>
          <small>
            @{node.username} · {formatDateOnly(node.created_at)} dan beri
          </small>
        </div>

        <div className="tree-role">
          <RoleBadge role={node.role} />
          {node.is_superuser ? <span className="badge badge-neutral">super</span> : null}
          {!node.is_active ? <span className="badge badge-muted">nofaol</span> : null}
        </div>

        <div className="tree-stats">
          <span title="Qurilmalar">
            <Icon name="database" size={14} />
            {node.device_count}
          </span>
          <span title="Qora ro'yxat">
            <Icon name="shield" size={14} />
            {node.blacklist_count}
          </span>
          <span title="Quyi bo'limlar">
            <Icon name="users" size={14} />
            {node.children?.length || 0}
          </span>
        </div>

        <div className="row-actions">
          <button
            type="button"
            className="icon-btn"
            title="Quyi bo'lim qo'shish"
            onClick={() => onAdd(node)}
          >
            <Icon name="plus" size={16} />
          </button>
          <button
            type="button"
            className="icon-btn"
            title="Tahrirlash"
            onClick={() => onEdit(node)}
          >
            <Icon name="edit" size={16} />
          </button>
          <button
            type="button"
            className="icon-btn icon-btn-danger"
            title="O'chirish"
            onClick={() => onDelete(node)}
            disabled={isSelf}
          >
            <Icon name="trash" size={16} />
          </button>
        </div>
      </div>

      {open && hasChildren ? (
        <div className="tree-children">
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              level={level + 1}
              expanded={expanded}
              toggle={toggle}
              onAdd={onAdd}
              onEdit={onEdit}
              onDelete={onDelete}
              currentUser={currentUser}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export default function Users() {
  const { user } = useAuth();
  const { notify } = useToast();

  const [tree, setTree] = useState([]);
  const [flatUsers, setFlatUsers] = useState([]);
  const [searchResults, setSearchResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState({});
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [presetParentId, setPresetParentId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [treeResponse, flatResponse] = await Promise.all([
        api.get("/api/users/tree"),
        api.get("/api/users"),
      ]);
      setTree(treeResponse.data);
      setFlatUsers(flatResponse.data);
    } catch (error) {
      notify(apiError(error, "Foydalanuvchilarni yuklab bo'lmadi"), "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const query = search.trim();
    if (!query) {
      setSearchResults(null);
      return undefined;
    }

    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const { data } = await api.get("/api/users", {
          params: { search: query },
          signal: controller.signal,
        });
        setSearchResults(data);
      } catch (error) {
        if (error.name !== "CanceledError" && error.code !== "ERR_CANCELED") {
          setSearchResults([]);
        }
      }
    }, 300);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [search]);

  function toggle(id) {
    setExpanded((current) => ({
      ...current,
      [id]: current[id] === false,
    }));
  }

  function openCreate(parent = null) {
    setEditing(null);
    setPresetParentId(parent ? parent.id : user?.id);
    setFormOpen(true);
  }

  function openEdit(target) {
    setEditing(target);
    setPresetParentId(target.parent_id);
    setFormOpen(true);
  }

  async function handleDelete(target) {
    const hasData =
      (target.children_count || 0) > 0 ||
      (target.device_count || 0) > 0 ||
      (target.blacklist_count || 0) > 0;

    const message = hasData
      ? `"${target.full_name || target.username}" va uning barcha quyi bo'limlari, qurilmalari hamda qora ro'yxat yozuvlari o'chiriladi. Davom etasizmi?`
      : `"${target.full_name || target.username}" foydalanuvchisini o'chirmoqchimisiz?`;

    if (!window.confirm(message)) return;

    try {
      await api.delete(`/api/users/${target.id}`, {
        params: hasData ? { force: "true" } : {},
      });
      notify("Foydalanuvchi o'chirildi", "success");
      load();
    } catch (error) {
      notify(apiError(error, "Foydalanuvchini o'chirib bo'lmadi"), "error");
    }
  }

  const parentNames = useMemo(() => {
    const map = new Map();
    flatUsers.forEach((item) => {
      map.set(item.id, item.full_name || item.username);
    });
    return map;
  }, [flatUsers]);

  return (
    <div className="page">
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <Icon name="users" size={15} />
            Ierarxiya
          </span>
          <h2>Foydalanuvchilar va bo'limlar</h2>
          <p>
            Har bir bo'lim o'zining va quyi bo'limlarning ma'lumotlarini ko'radi.
            Yangi foydalanuvchi qo'shish orqali tashkiliy tuzilmani
            kengaytiring.
          </p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => openCreate(null)}>
          <Icon name="plus" size={16} />
          Foydalanuvchi qo'shish
        </button>
      </section>

      <section className="panel">
        <header className="panel-head">
          <div>
            <h2>Tashkiliy tuzilma</h2>
            <p>Jami {flatUsers.length} ta ko'rinadigan foydalanuvchi</p>
          </div>
        </header>

        <div className="toolbar">
          <div className="search-box">
            <Icon name="search" size={17} />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Login, F.I.Sh yoki rol bo'yicha qidirish..."
            />
            {search ? (
              <button
                type="button"
                className="input-action"
                onClick={() => setSearch("")}
                aria-label="Qidiruvni tozalash"
              >
                <Icon name="close" size={15} />
              </button>
            ) : null}
          </div>
          <span className="toolbar-count">
            {searchResults ? <b>{searchResults.length}</b> : <b>{flatUsers.length}</b>} ta
            natija
          </span>
          <button type="button" className="btn btn-ghost btn-sm" onClick={load}>
            <Icon name="refresh" size={14} />
            Yangilash
          </button>
        </div>

        {loading ? (
          <div className="table-state inline">
            <span className="spinner spinner-sm" />
            Yuklanmoqda...
          </div>
        ) : searchResults ? (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Foydalanuvchi</th>
                  <th>Login</th>
                  <th>Rol</th>
                  <th>Ota</th>
                  <th className="text-center">Qurilmalar</th>
                  <th className="text-center">Qora ro'yxat</th>
                  <th className="col-actions">Amallar</th>
                </tr>
              </thead>
              <tbody>
                {searchResults.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="table-state">
                      <Icon name="search" size={22} />
                      <strong>Foydalanuvchi topilmadi</strong>
                    </td>
                  </tr>
                ) : (
                  searchResults.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <div className="person-cell">
                          <span className="avatar avatar-sm">
                            {initials(item.full_name, item.username?.[0])}
                          </span>
                          <div>
                            <strong>{item.full_name || item.username}</strong>
                            <small className="muted">{formatDateOnly(item.created_at)}</small>
                          </div>
                        </div>
                      </td>
                      <td className="mono">@{item.username}</td>
                      <td>
                        <RoleBadge role={item.role} />
                      </td>
                      <td>{item.parent_id ? parentNames.get(item.parent_id) || "—" : "Ildiz"}</td>
                      <td className="text-center">{item.device_count}</td>
                      <td className="text-center">{item.blacklist_count}</td>
                      <td className="col-actions">
                        <div className="row-actions">
                          <button
                            type="button"
                            className="icon-btn"
                            title="Quyi bo'lim qo'shish"
                            onClick={() => openCreate(item)}
                          >
                            <Icon name="plus" size={16} />
                          </button>
                          <button
                            type="button"
                            className="icon-btn"
                            title="Tahrirlash"
                            onClick={() => openEdit(item)}
                          >
                            <Icon name="edit" size={16} />
                          </button>
                          <button
                            type="button"
                            className="icon-btn icon-btn-danger"
                            title="O'chirish"
                            onClick={() => handleDelete(item)}
                            disabled={item.id === user?.id}
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
        ) : (
          <div className="tree">
            {tree.length === 0 ? (
              <div className="table-state inline">
                <Icon name="users" size={22} />
                <strong>Foydalanuvchilar yo'q</strong>
              </div>
            ) : (
              tree.map((node) => (
                <TreeNode
                  key={node.id}
                  node={node}
                  level={0}
                  expanded={expanded}
                  toggle={toggle}
                  onAdd={openCreate}
                  onEdit={openEdit}
                  onDelete={handleDelete}
                  currentUser={user}
                />
              ))
            )}
          </div>
        )}
      </section>

      <UserFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        user={editing}
        currentUser={user}
        allUsers={flatUsers}
        presetParentId={presetParentId}
        onSaved={load}
      />
    </div>
  );
}
