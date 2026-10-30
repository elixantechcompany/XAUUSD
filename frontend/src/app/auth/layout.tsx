/**
 * Auth layout — no sidebar, no top bar, no bottom nav.
 * Auth pages are full-screen, centred forms.
 */
export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-background">
      {children}
    </div>
  );
}
