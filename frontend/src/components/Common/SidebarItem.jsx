export function SidebarItem({
  icon: Icon,
  label,
  count,
  active,
  onClick,
}) {
  return (
    <button
      className={active ? "sidebar-item active" : "sidebar-item"}
      onClick={onClick}
      title={label}
    >
      <Icon size={15} />
      <span>{label}</span>
      {count !== undefined && <small>{count}</small>}
    </button>
  );
}
