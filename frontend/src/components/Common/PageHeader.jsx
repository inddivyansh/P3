export function PageHeader({
  eyebrow,
  title,
  description,
  systemOnline,
}) {
  return (
    <div className="page-header">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {systemOnline !== undefined && (
        <div
          className={`header-status ${
            systemOnline ? "online" : "offline"
          }`}
        >
          <span className={systemOnline ? "online-dot" : "offline-dot"} />
          {systemOnline ? "SYSTEM OPERATIONAL" : "SYSTEM OFFLINE"}
        </div>
      )}
    </div>
  );
}
