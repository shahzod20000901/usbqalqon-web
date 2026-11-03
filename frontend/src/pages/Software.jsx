import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import api, { apiError } from "../api";
import Icon from "../components/Icon";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { downloadBlob, formatDate } from "../utils";

function formatBytes(value) {
  const size = Number(value) || 0;
  if (size <= 0) return "—";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(2)} MB`;
}

function UploadPackage({ onUploaded }) {
  const { notify } = useToast();
  const [file, setFile] = useState(null);
  const [version, setVersion] = useState("");
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef(null);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!file) {
      notify("Avval .exe faylni tanlang", "error");
      return;
    }
    if (!file.name.toLowerCase().endsWith(".exe")) {
      notify("Faqat .exe fayl yuklash mumkin", "error");
      return;
    }

    const data = new FormData();
    data.append("file", file);
    if (version.trim()) data.append("version", version.trim());

    setUploading(true);
    try {
      const response = await api.post("/api/software/package", data, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      notify("Agent paketi yangilandi", "success");
      setFile(null);
      setVersion("");
      if (inputRef.current) inputRef.current.value = "";
      onUploaded?.(response.data);
    } catch (error) {
      notify(apiError(error, "Agent paketini yuklab bo'lmadi"), "error");
    } finally {
      setUploading(false);
    }
  }

  return (
    <form className="upload-panel" onSubmit={handleSubmit}>
      <label className="dropzone">
        <Icon name="upload" size={28} />
        <strong>{file ? file.name : "Agent .exe faylini tanlang"}</strong>
        <small>Windows uchun yagona agent. Maksimal hajm: 200 MB.</small>
        <input
          ref={inputRef}
          type="file"
          accept=".exe,application/octet-stream"
          onChange={(event) => setFile(event.target.files?.[0] || null)}
        />
      </label>

      <div className="upload-meta">
        <label className="field">
          <span>Versiya (ixtiyoriy)</span>
          <input
            value={version}
            onChange={(event) => setVersion(event.target.value)}
            placeholder="1.0.0"
            maxLength={64}
          />
        </label>
        <button type="submit" className="btn btn-primary" disabled={uploading || !file}>
          <Icon name="upload" size={16} />
          {uploading ? "Yuklanmoqda..." : "Agentni yuklash"}
        </button>
      </div>
    </form>
  );
}

export default function Software() {
  const { user } = useAuth();
  const { notify } = useToast();
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const isSuperuser = Boolean(user?.is_superuser || info?.is_superuser);
  const packageInfo = info?.package;

  useEffect(() => {
    let cancelled = false;
    api
      .get("/api/software/info")
      .then(({ data }) => {
        if (!cancelled) setInfo(data);
      })
      .catch((error) => {
        if (!cancelled) notify(apiError(error, "Ma'lumotni yuklab bo'lmadi"), "error");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [notify]);

  async function handleDownload() {
    if (!packageInfo) {
      notify("Agent paketi hali yuklanmagan", "error");
      return;
    }
    setDownloading(true);
    try {
      const response = await api.get("/api/software/package/download", {
        responseType: "blob",
      });
      downloadBlob(response.data, packageInfo.original_filename || "USBQalqonAgent.exe");
      notify("Agent yuklab olindi. Uni administrator sifatida ishga tushiring.", "success");
    } catch (error) {
      notify(apiError(error, "Agentni yuklab bo'lmadi"), "error");
    } finally {
      setDownloading(false);
    }
  }

  async function handleDeletePackage() {
    if (!window.confirm("Agent paketini o'chirmoqchimisiz? Foydalanuvchilar yuklab ololmaydi.")) {
      return;
    }
    setDeleting(true);
    try {
      await api.delete("/api/software/package");
      setInfo((current) => ({ ...current, package: null }));
      notify("Agent paketi o'chirildi", "success");
    } catch (error) {
      notify(apiError(error, "Paketni o'chirib bo'lmadi"), "error");
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <div className="page">
        <div className="panel table-state inline">
          <span className="spinner spinner-sm" />
          Yuklanmoqda...
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <section className="page-intro software-intro">
        <div>
          <span className="eyebrow">
            <Icon name="download" size={15} />
            Agent tarqatish
          </span>
          <h2>Windows uchun yagona USB Qalqon agenti</h2>
          <p>
            Agent kompyuterga ulangan USB qurilmalarni tekshiradi, ruxsat
            etilmaganlarini web tizimga yuboradi va qora ro'yxatga yozdiradi.
            Agent tizimga login va parol orqali kiradi.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-primary btn-lg"
          onClick={handleDownload}
          disabled={downloading || !packageInfo}
        >
          <Icon name="download" size={18} />
          {downloading ? "Tayyorlanmoqda..." : "Agentni yuklab olish"}
        </button>
      </section>

      {!packageInfo ? (
        <div className="callout callout-warning">
          <Icon name="alert" size={18} />
          <p>
            {isSuperuser
              ? "Agent paketi hali yuklanmagan. Quyidagi bo'lim orqali .exe faylni yuklang — shundan so'ng barcha foydalanuvchilar yuklab olishi mumkin bo'ladi."
              : "Agent paketi hali superadmin tomonidan yuklanmagan. Iltimos, tizim administratoriga murojaat qiling."}
          </p>
        </div>
      ) : null}

      <section>
        <div className="panel">
          <header className="panel-head compact">
            <div>
              <h2>Agent paketi</h2>
              <p>Superadmin tomonidan yuklangan yagona .exe fayl</p>
            </div>
            {packageInfo ? (
              <span className="badge badge-success">
                <span className="status-dot" />
                Yuklangan
              </span>
            ) : (
              <span className="badge badge-muted">Yo'q</span>
            )}
          </header>

          {packageInfo ? (
            <div className="package-card">
              <span className="package-icon">
                <Icon name="download" size={24} />
              </span>
              <div className="package-main">
                <strong>{packageInfo.original_filename}</strong>
                <small>
                  Versiya {packageInfo.version || "—"} · {formatBytes(packageInfo.size)}
                </small>
                <small>
                  Yuklangan: {formatDate(packageInfo.uploaded_at)}
                </small>
                <code className="package-hash" title={packageInfo.sha256}>
                  SHA-256: {packageInfo.sha256?.slice(0, 24)}…
                </code>
              </div>
            </div>
          ) : (
            <div className="package-empty">
              <Icon name="file" size={26} />
              <p>Hozircha agent fayli yuklanmagan.</p>
            </div>
          )}

          <div className="package-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleDownload}
              disabled={downloading || !packageInfo}
            >
              <Icon name="download" size={16} />
              {downloading ? "Yuklanmoqda..." : "Yuklab olish"}
            </button>
            {isSuperuser ? (
              <Link to="/docs" className="btn btn-ghost">
                <Icon name="book" size={16} />
                API hujjati
              </Link>
            ) : null}
            {isSuperuser && packageInfo ? (
              <button
                type="button"
                className="btn btn-danger-ghost"
                onClick={handleDeletePackage}
                disabled={deleting}
              >
                <Icon name="trash" size={16} />
                {deleting ? "O'chirilmoqda..." : "Paketni o'chirish"}
              </button>
            ) : null}
          </div>

          {isSuperuser ? (
            <div className="upload-section">
              <div className="upload-section-head">
                <div>
                  <strong>Yangi agent yuklash</strong>
                  <small>Yuklanganda avvalgi paket almashtiriladi.</small>
                </div>
              </div>
              <UploadPackage
                onUploaded={(uploaded) =>
                  setInfo((current) => ({ ...current, package: uploaded }))
                }
              />
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}
