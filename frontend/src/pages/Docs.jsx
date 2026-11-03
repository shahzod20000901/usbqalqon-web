import { useMemo } from "react";
import { Navigate } from "react-router-dom";
import { TOKEN_KEY } from "../api";
import Icon from "../components/Icon";
import { useAuth } from "../context/AuthContext";

export default function Docs() {
  const { user } = useAuth();
  const token = localStorage.getItem(TOKEN_KEY) || "";

  if (!user?.is_superuser) {
    return <Navigate to="/" replace />;
  }

  const docsUrl = useMemo(() => `/docs?token=${encodeURIComponent(token)}`, [token]);
  const openapiUrl = useMemo(() => `/openapi.json?token=${encodeURIComponent(token)}`, [token]);

  return (
    <div className="page docs-page">
      <section className="page-intro docs-intro">
        <div>
          <span className="eyebrow">
            <Icon name="book" size={15} />
            API hujjati
          </span>
          <h2>Swagger / OpenAPI</h2>
          <p>
            USB Qalqon tizimining barcha API endpointlari, sxemalari va
            autentifikatsiya parametrlari. Ushbu bo'lim faqat tizim
            administratori uchun ochiq.
          </p>
        </div>
        <div className="docs-actions">
          <a className="btn btn-primary" href={docsUrl} target="_blank" rel="noreferrer">
            <Icon name="external" size={16} />
            Yangi oynada ochish
          </a>
          <a className="btn btn-ghost" href={openapiUrl} target="_blank" rel="noreferrer">
            <Icon name="file" size={16} />
            openapi.json
          </a>
        </div>
      </section>

      <section className="panel docs-panel">
        <iframe
          className="docs-frame"
          src={docsUrl}
          title="USB Qalqon API — Swagger UI"
        />
      </section>
    </div>
  );
}
