type EmptyProps = {
  title: string;
  description: string;
};

export default function Empty({ title, description }: EmptyProps) {
  return (
    <div className="empty-state" role="status">
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
