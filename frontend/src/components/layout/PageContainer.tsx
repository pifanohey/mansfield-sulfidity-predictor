interface PageContainerProps {
  children: React.ReactNode;
}

export default function PageContainer({ children }: PageContainerProps) {
  return (
    <main className="flex-1 overflow-auto px-6 py-6">{children}</main>
  );
}
