export default function EmptyState({ label }: { label: string }) {
  return (
    <div className="card py-10 text-center">
      <p className="text-sm text-muted">{label}</p>
    </div>
  );
}
