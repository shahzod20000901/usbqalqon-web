import { useCallback, useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import api, { apiError } from "../api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { formatDate, initials } from "../utils";
import Icon from "./Icon";
import Modal from "./Modal";

const NAV_ITEMS = [
  {
    to: "/",
    label: "Bosh sahifa",
    hint: "Barcha qurilmalar",
    icon: "home",
    end: true,
  },
  {
    to: "/blacklist",
    label: "Qora ro'yxat",
    hint: "Ruxsat etilmagan qurilmalar",
    icon: "shield",
  },
  {
    to: "/users",
    label: "Foydalanuvchilar",
    hint: "Tashkiliy tuzilma",
    icon: "users",
  },
  {
    to: "/software",
    label: "Dasturiy ta'minot",
    hint: "Desktop agentlar",
    icon: "download",
  },
  {
    to: "/docs",
    label: "API hujjati",
    hint: "Swagger /docs",
    icon: "book",
    adminOnly: true,
  },
];

const TITLES = {
  "/": "Bosh sahifa",
  "/blacklist": "Qora ro'yxat",
  "/users": "Foydalanuvchilar",
  "/software": "Dasturiy ta'minot",
  "/docs": "API hujjati",
};

function NotificationBell() {
  const { notify } = useToast();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const wrapRef = useRef(null);
  const previousUnread = useRef(null);

  const loadUnread = useCallback(
    async (announce = false) => {
      try {
        const { data } = await api.get("/api/notifications/unread-count");
        const count = data.unread || 0;
        if (
          announce &&
          previousUnread.current !== null &&
          count > previousUnread.current
        ) {
          notify(
            `Yangi bildirishnoma: ${count - previousUnread.current} ta`,
            "info"
          );
          window.dispatchEvent(new Event("usbqalqon:blacklist-changed"));
        }
        previousUnread.current = count;
        setUnread(count);
      } catch {
        /* bildirishnomalar ixtiyoriy */
      }
    },
    [notify]
  );

  const loadItems = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/api/notifications", {
        params: { page: 1, page_size: 8 },
      });
      const count = data.unread || 0;
      if (previousUnread.current !== null && count > previousUnread.current) {
        notify(`Yangi bildirishnoma: ${count - previousUnread.current} ta`, "info");
        window.dispatchEvent(new Event("usbqalqon:blacklist-changed"));
      }
      setItems(data.items || []);
      setUnread(count);
      previousUnread.current = count;
    } catch (error) {
      notify(apiError(error, "Bildirishnomalarni yuklab bo'lmadi"), "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    loadUnread();
    const timer = setInterval(() => loadUnread(true), 10000);
    return () => clearInterval(timer);
  }, [loadUnread]);

  useEffect(() => {
    if (!open) return undefined;
    loadItems();
    const timer = setInterval(loadItems, 10000);
    const onPointerDown = (event) => {
      if (wrapRef.current && !wrapRef.current.contains(event.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => {
      clearInterval(timer);
      document.removeEventListener("mousedown", onPointerDown);
    };
  }, [open, loadItems]);

  async function markRead(item) {
    if (!item.is_read) {
      try {
        await api.post(`/api/notifications/${item.id}/read`);
        setItems((current) =>
          current.map((entry) =>
            entry.id === item.id ? { ...entry, is_read: true } : entry
          )
        );
        setUnread((value) => Math.max(0, value - 1));
        window.dispatchEvent(new Event("usbqalqon:blacklist-changed"));
      } catch {
        /* davom etamiz */
      }
    }
    setOpen(false);
    navigate("/blacklist");
  }

  async function markAllRead() {
    try {
      await api.post("/api/notifications/read-all");
      setItems((current) => current.map((entry) => ({ ...entry, is_read: true })));
      setUnread(0);
      previousUnread.current = 0;
      window.dispatchEvent(new Event("usbqalqon:blacklist-changed"));
    } catch (error) {
      notify(apiError(error, "Bildirishnomalarni belgilab bo'lmadi"), "error");
    }
  }

  return (
    <div className="notif-wrap" ref={wrapRef}>
      <button
        type="button"
        className={`icon-btn notif-btn ${open ? "active" : ""}`}
        onClick={() => setOpen((value) => !value)}
        aria-label="Bildirishnomalar"
        title="Bildirishnomalar"
      >
        <Icon name="bell" size={19} />
        {unread > 0 ? <span className="notif-badge">{unread > 99 ? "99+" : unread}</span> : null}
      </button>

      {open ? (
        <div className="notif-menu">
          <header className="notif-head">
            <div>
              <strong>Bildirishnomalar</strong>
              <small>{unread} ta o'qilmagan</small>
            </div>
            <button
              type="button"
              className="btn btn-ghost btn-xs"
              onClick={markAllRead}
              disabled={unread === 0}
            >
              <Icon name="check" size={13} />
              Barchasi o'qildi
            </button>
          </header>

          <div className="notif-list">
            {loading ? (
              <div className="notif-state">
                <span className="spinner spinner-sm" />
                Yuklanmoqda...
              </div>
            ) : items.length === 0 ? (
              <div className="notif-state">
                <Icon name="bell" size={20} />
                <strong>Bildirishnoma yo'q</strong>
                <span>Yangi qora ro'yxat hodisalari shu yerda ko'rinadi</span>
              </div>
            ) : (
              items.map((item) => (
                <button
                  type="button"
                  key={item.id}
                  className={`notif-item ${item.is_read ? "" : "unread"}`}
                  onClick={() => markRead(item)}
                >
                  <span className="notif-icon">
                    <Icon name={item.kind === "blacklist" ? "shield" : "info"} size={16} />
                  </span>
                  <span className="notif-body">
                    <strong>{item.title}</strong>
                    <span>{item.message}</span>
                    <small>{formatDate(item.created_at)}</small>
                  </span>
                  {item.is_read ? null : <span className="notif-dot" />}
                </button>
              ))
            )}
          </div>

          <footer className="notif-foot">
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => {
                setOpen(false);
                navigate("/blacklist");
              }}
            >
              Qora ro'yxatni ko'rish
              <Icon name="chevron" size={14} />
            </button>
          </footer>
        </div>
      ) : null}
    </div>
  );
}

function PasswordModal({ open, onClose }) {
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [saving, setSaving] = useState(false);
  const { notify } = useToast();

  function reset() {
    setOldPassword("");
    setNewPassword("");
    setRepeat("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (newPassword.length < 4) {
      notify("Yangi parol kamida 4 belgidan iborat bo'lsin", "error");
      return;
    }
    if (newPassword !== repeat) {
      notify("Yangi parollar mos kelmadi", "error");
      return;
    }
    setSaving(true);
    try {
      await api.post("/api/auth/change-password", {
        old_password: oldPassword,
        new_password: newPassword,
      });
      notify("Parol muvaffaqiyatli almashtirildi", "success");
      reset();
      onClose();
    } catch (error) {
      notify(apiError(error, "Parolni almashtirib bo'lmadi"), "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={() => {
        reset();
        onClose();
      }}
      title="Parolni almashtirish"
      subtitle="Xavfsizlik uchun eski parolni kiriting"
      size="sm"
      footer={
        <>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => {
              reset();
              onClose();
            }}
          >
            Bekor qilish
          </button>
          <button
            type="submit"
            form="password-form"
            className="btn btn-primary"
            disabled={saving}
          >
            {saving ? "Saqlanmoqda..." : "Saqlash"}
          </button>
        </>
      }
    >
      <form id="password-form" className="form-grid" onSubmit={handleSubmit}>
        <label className="field field-full">
          <span>Eski parol</span>
          <input
            type="password"
            value={oldPassword}
            onChange={(event) => setOldPassword(event.target.value)}
            required
            autoComplete="current-password"
          />
        </label>
        <label className="field field-full">
          <span>Yangi parol</span>
          <input
            type="password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            required
            minLength={4}
            autoComplete="new-password"
          />
        </label>
        <label className="field field-full">
          <span>Yangi parolni takrorlang</span>
          <input
            type="password"
            value={repeat}
            onChange={(event) => setRepeat(event.target.value)}
            required
            minLength={4}
            autoComplete="new-password"
          />
        </label>
      </form>
    </Modal>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);

  const title = TITLES[location.pathname] || "USB Qalqon";

  return (
    <div className="app-shell">
      {mobileOpen ? (
        <button
          type="button"
          className="sidebar-overlay"
          onClick={() => setMobileOpen(false)}
          aria-label="Menyuni yopish"
        />
      ) : null}

      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <span className="brand-mark">
            <Icon name="shield" size={26} />
          </span>
          <div>
            <strong>USB Qalqon</strong>
            <small>Web boshqaruv</small>
          </div>
          <button
            type="button"
            className="icon-btn sidebar-close"
            onClick={() => setMobileOpen(false)}
            aria-label="Yopish"
          >
            <Icon name="close" size={18} />
          </button>
        </div>

        <nav className="nav">
          <span className="nav-label">Menyu</span>
          {NAV_ITEMS.filter((item) => !item.adminOnly || user?.is_superuser).map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
            >
              <span className="nav-icon">
                <Icon name={item.icon} size={19} />
              </span>
              <span className="nav-text">
                <strong>{item.label}</strong>
                <small>{item.hint}</small>
              </span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-card">
            <span className="avatar">{initials(user?.full_name, user?.username?.[0])}</span>
            <div className="user-meta">
              <strong>{user?.full_name || user?.username}</strong>
              <small>
                @{user?.username}
                {user?.is_superuser ? " · administrator" : ""}
              </small>
            </div>
          </div>
          <div className="sidebar-actions">
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => setPasswordOpen(true)}
            >
              <Icon name="key" size={15} />
              Parol
            </button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={logout}>
              <Icon name="logout" size={15} />
              Chiqish
            </button>
          </div>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <button
            type="button"
            className="icon-btn mobile-menu"
            onClick={() => setMobileOpen(true)}
            aria-label="Menyuni ochish"
          >
            <Icon name="menu" size={20} />
          </button>
          <div className="topbar-title">
            <h1>{title}</h1>
            <p>
              {user?.is_superuser
                ? "Tizimning barcha ma'lumotlari ko'rinadi"
                : "Faqat sizga tegishli bo'lim ma'lumotlari"}
            </p>
          </div>
          <div className="topbar-actions">
            <NotificationBell />
            <div className="topbar-user">
              <span className="avatar avatar-sm">
                {initials(user?.full_name, user?.username?.[0])}
              </span>
              <div>
                <strong>{user?.full_name || user?.username}</strong>
                <small>{user?.role || "foydalanuvchi"}</small>
              </div>
            </div>
          </div>
        </header>

        <main className="content">
          <Outlet />
        </main>
      </div>

      <PasswordModal open={passwordOpen} onClose={() => setPasswordOpen(false)} />
    </div>
  );
}
